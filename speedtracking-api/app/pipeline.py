"""
Async delivery pipeline and in-memory state store.

Each delivery goes through these stages once MinIO fires its webhook:
  uploaded → detecting → tracking → calculating → complete (or failed)

State is held in process memory with a 1-hour TTL.  A real deployment should
swap DeliveryStore for Redis; the interface is intentionally narrow so that
swap is a single-file change.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import boto3

from .schemas import AnalyzeDeliveryConfig
from .services import BootstrapAnalysisService

logger = logging.getLogger(__name__)

_DELIVERY_TTL_SECONDS = 3600  # 1 hour

_analysis_service = BootstrapAnalysisService()


# ── SSE event ────────────────────────────────────────────────────────────────


@dataclass
class DeliveryEvent:
    event: str  # e.g. "uploaded", "detecting", "complete", "failed"
    data: Any  # plain string or JSON-serialisable dict


# ── Per-delivery state ────────────────────────────────────────────────────────


@dataclass
class DeliveryState:
    delivery_id: str
    bucket: str
    object_key: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    events: list[DeliveryEvent] = field(default_factory=list)
    done: bool = False
    cursor: int = 0  # next unread event index for streaming consumers

    def append(self, event: DeliveryEvent) -> None:
        self.events.append(event)

    def is_expired(self) -> bool:
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > _DELIVERY_TTL_SECONDS


# ── In-memory store ───────────────────────────────────────────────────────────


class DeliveryStore:
    """Thread-safe in-memory delivery state store."""

    def __init__(self) -> None:
        self._store: dict[str, DeliveryState] = {}
        self._lock = asyncio.Lock()

    async def create(self, delivery_id: str, bucket: str, object_key: str) -> DeliveryState:
        async with self._lock:
            state = DeliveryState(
                delivery_id=delivery_id,
                bucket=bucket,
                object_key=object_key,
            )
            self._store[delivery_id] = state
            return state

    async def get(self, delivery_id: str) -> DeliveryState | None:
        async with self._lock:
            return self._store.get(delivery_id)

    async def append_event(self, delivery_id: str, event: DeliveryEvent) -> None:
        async with self._lock:
            state = self._store.get(delivery_id)
            if state is not None:
                state.append(event)

    async def mark_done(self, delivery_id: str) -> None:
        async with self._lock:
            state = self._store.get(delivery_id)
            if state is not None:
                state.done = True

    async def purge_expired(self) -> int:
        async with self._lock:
            expired = [k for k, v in self._store.items() if v.is_expired()]
            for k in expired:
                del self._store[k]
            return len(expired)


# Global store instance shared across the FastAPI app
delivery_store = DeliveryStore()


# ── MinIO / S3 client helpers ─────────────────────────────────────────────────


def _make_s3_client() -> Any:
    endpoint_url = os.environ.get("MINIO_ENDPOINT_URL", "http://minio:9000")
    access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",  # MinIO ignores region but boto3 requires it
    )


def _download_video(bucket: str, object_key: str) -> bytes:
    """Download video bytes from MinIO/S3.  Returns empty bytes on any error."""
    body = None
    try:
        client = _make_s3_client()
        response = client.get_object(Bucket=bucket, Key=object_key)
        body = response["Body"]
        return body.read()
    except Exception as exc:  # noqa: BLE001 — covers ClientError, EndpointConnectionError, etc.
        logger.warning("Could not download video s3://%s/%s: %s", bucket, object_key, exc)
        return b""
    finally:
        if body is not None:
            try:
                body.close()
            except Exception:  # noqa: BLE001
                pass


def _delete_video(bucket: str, object_key: str) -> None:
    """Remove video from MinIO/S3 after processing."""
    try:
        client = _make_s3_client()
        client.delete_object(Bucket=bucket, Key=object_key)
        logger.info("Deleted s3://%s/%s", bucket, object_key)
    except ClientError as exc:
        logger.warning("Could not delete video s3://%s/%s: %s", bucket, object_key, exc)


# ── Pipeline stages ───────────────────────────────────────────────────────────


def _extract_delivery_id(object_key: str) -> str:
    """Parse delivery_id from object key 'deliveries/{delivery_id}/video.mp4'."""
    parts = object_key.strip("/").split("/")
    if len(parts) >= 2:
        return parts[1]
    return parts[0]


def _build_config_from_env() -> AnalyzeDeliveryConfig:
    """
    Build a minimal AnalyzeDeliveryConfig using defaults.

    In the full pipeline the configuration will be stored by the middleware
    when the presigned URL is requested, then looked up here by delivery_id.
    For the bootstrap pipeline we use sensible defaults.
    """
    return AnalyzeDeliveryConfig(
        pitch_length_meters=22.0,
        ball_color="red",
        ball_weight_grams=156,
        bowling_style="fast",
        bowler_height_cm=180,
    )


async def run_pipeline(delivery_id: str, bucket: str, object_key: str) -> None:
    """
    Async pipeline triggered by a MinIO webhook event.

    Stages:
      1. uploaded    — acknowledge receipt
      2. detecting   — ball detection (YOLO+SAHI; bootstrap for now)
      3. tracking    — ByteTrack + Kalman (bootstrap for now)
      4. calculating — physics engine (bootstrap for now)
      5. complete    — final AnalyzeDeliveryResponse payload
    """
    try:
        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="uploaded", data="Video received, starting analysis"),
        )

        # Download video from MinIO
        video_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _download_video, bucket, object_key
        )

        if not video_bytes:
            await delivery_store.append_event(
                delivery_id,
                DeliveryEvent(
                    event="failed",
                    data=f"Could not download video from s3://{bucket}/{object_key}",
                ),
            )
            await delivery_store.mark_done(delivery_id)
            return

        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="detecting", data="Detecting ball trajectory"),
        )

        # Bootstrap analysis (replace with real YOLO+SAHI when model is available)
        config = _build_config_from_env()
        video_name = object_key.split("/")[-1] or "delivery.mp4"

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            _analysis_service.analyze,
            video_name,
            video_bytes,
            config,
        )

        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="tracking", data="Tracking ball across frames"),
        )

        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="calculating", data="Calculating speed and biomechanics"),
        )

        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="complete", data=result.model_dump()),
        )

        # Cleanup: remove video from MinIO
        await asyncio.get_event_loop().run_in_executor(
            None, _delete_video, bucket, object_key
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for delivery %s: %s", delivery_id, exc)
        await delivery_store.append_event(
            delivery_id,
            DeliveryEvent(event="failed", data=str(exc)),
        )
    finally:
        await delivery_store.mark_done(delivery_id)
