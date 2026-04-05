import asyncio
import json
import logging

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .config import get_settings, load_default_inference_config
from .pipeline import DeliveryEvent, delivery_store, run_pipeline
from .schemas import AnalyzeDeliveryConfig, AnalyzeDeliveryResponse, MinioWebhookPayload
from .services import BootstrapAnalysisService

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SpeedTracking API",
    version="0.1.0",
    description="Bootstrap FastAPI service for delivery analysis contracts",
)

analysis_service = BootstrapAnalysisService()


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "analysis_mode": settings.analysis_mode,
    }


def build_config(configurations: str) -> AnalyzeDeliveryConfig:
    try:
        payload = json.loads(configurations)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="configurations must be valid JSON") from exc

    merged_payload = {
        **load_default_inference_config(),
        **payload,
    }

    try:
        return AnalyzeDeliveryConfig.model_validate(merged_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/deliveries/analyze", response_model=AnalyzeDeliveryResponse)
async def analyze_delivery(
    video: UploadFile = File(...),
    configurations: str = Form(...),
) -> AnalyzeDeliveryResponse:
    video_bytes = await video.read()
    if not video_bytes:
        raise HTTPException(status_code=400, detail="video must not be empty")

    config = build_config(configurations)
    return analysis_service.analyze(
        video_name=video.filename or "delivery.mp4",
        video_bytes=video_bytes,
        config=config,
    )


# ── Async pipeline endpoints ──────────────────────────────────────────────────


@app.post("/webhooks/minio")
async def minio_webhook(
    payload: MinioWebhookPayload,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Receives MinIO s3:ObjectCreated:Put events.

    MinIO fires this webhook when a video is uploaded to the deliveries bucket.
    The object key is expected to follow the pattern:
      deliveries/{delivery_id}/video.mp4
    """
    if not payload.EventName.startswith("s3:ObjectCreated"):
        return JSONResponse(
            status_code=200,
            content={"accepted": False, "reason": "unhandled event type"},
        )

    bucket = payload.bucket()
    object_key = payload.object_key()

    # Extract delivery_id: second path segment of the object key
    parts = object_key.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Unexpected object key format: {object_key!r}. Expected deliveries/{{delivery_id}}/video.mp4",
        )

    delivery_id = parts[1] if parts[0] == "deliveries" else parts[0]

    await delivery_store.create(
        delivery_id=delivery_id,
        bucket=bucket,
        object_key=object_key,
    )

    background_tasks.add_task(run_pipeline, delivery_id, bucket, object_key)

    logger.info("Accepted pipeline for delivery %s (s3://%s/%s)", delivery_id, bucket, object_key)
    return JSONResponse(
        status_code=202,
        content={"accepted": True, "delivery_id": delivery_id},
    )


@app.get("/api/v1/deliveries/{delivery_id}/events")
async def stream_delivery_events(delivery_id: str) -> EventSourceResponse:
    """
    Server-Sent Events endpoint for delivery pipeline progress.

    Emits events in order:
      uploaded → detecting → tracking → calculating → complete | failed
    """
    state = await delivery_store.get(delivery_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"delivery {delivery_id!r} not found")

    async def event_generator():
        cursor = 0
        while True:
            state = await delivery_store.get(delivery_id)
            if state is None:
                break

            while cursor < len(state.events):
                ev: DeliveryEvent = state.events[cursor]
                cursor += 1
                data = ev.data if isinstance(ev.data, str) else json.dumps(ev.data)
                yield {"event": ev.event, "data": data}

            if state.done:
                break

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())