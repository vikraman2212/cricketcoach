"""
Tests for the async delivery pipeline endpoints:
  POST /webhooks/minio
  GET  /api/v1/deliveries/{delivery_id}/events
"""

import asyncio
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.pipeline import DeliveryEvent, delivery_store


@pytest_asyncio.fixture(autouse=True)
async def clear_store():
    """Reset delivery store between tests."""
    delivery_store._store.clear()
    yield
    delivery_store._store.clear()


@pytest.fixture
def minio_put_payload():
    return {
        "EventName": "s3:ObjectCreated:Put",
        "Key": "deliveries/test-delivery-123/video.mp4",
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "deliveries"},
                    "object": {"key": "deliveries/test-delivery-123/video.mp4"},
                }
            }
        ],
    }


@pytest.fixture
def async_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── MinIO webhook ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_minio_webhook_accepts_object_created(async_client, minio_put_payload):
    async with async_client as client:
        response = await client.post("/webhooks/minio", json=minio_put_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["delivery_id"] == "test-delivery-123"


@pytest.mark.asyncio
async def test_minio_webhook_ignores_non_create_event(async_client):
    async with async_client as client:
        response = await client.post(
            "/webhooks/minio",
            json={
                "EventName": "s3:ObjectRemoved:Delete",
                "Key": "deliveries/abc/video.mp4",
                "Records": [],
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is False


@pytest.mark.asyncio
async def test_minio_webhook_rejects_invalid_object_key(async_client):
    async with async_client as client:
        response = await client.post(
            "/webhooks/minio",
            json={
                "EventName": "s3:ObjectCreated:Put",
                "Key": "bad",
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": "deliveries"},
                            "object": {"key": "bad"},
                        }
                    }
                ],
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_minio_webhook_creates_delivery_state(async_client, minio_put_payload):
    async with async_client as client:
        await client.post("/webhooks/minio", json=minio_put_payload)

    state = await delivery_store.get("test-delivery-123")
    assert state is not None
    assert state.bucket == "deliveries"
    assert state.object_key == "deliveries/test-delivery-123/video.mp4"


# ── SSE events endpoint ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stream_returns_404_for_unknown_delivery(async_client):
    async with async_client as client:
        response = await client.get("/api/v1/deliveries/no-such-id/events")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_delivers_pre_populated_events():
    """
    Manually populate a delivery state and verify the SSE endpoint streams
    all events and closes when done=True.
    """
    delivery_id = "stream-test-001"
    state = await delivery_store.create(
        delivery_id=delivery_id,
        bucket="deliveries",
        object_key=f"deliveries/{delivery_id}/video.mp4",
    )
    state.append(DeliveryEvent(event="uploaded", data="Video received"))
    state.append(DeliveryEvent(event="complete", data={"speed_kmh": 120.0}))
    state.done = True

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/deliveries/{delivery_id}/events")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    raw = response.text
    assert "event: uploaded" in raw
    assert "Video received" in raw
    assert "event: complete" in raw
    assert "speed_kmh" in raw


# ── DeliveryStore unit tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delivery_store_create_and_get():
    state = await delivery_store.create("d1", "bucket", "key/d1/video.mp4")
    assert state.delivery_id == "d1"
    assert state.bucket == "bucket"

    fetched = await delivery_store.get("d1")
    assert fetched is not None
    assert fetched.delivery_id == "d1"


@pytest.mark.asyncio
async def test_delivery_store_append_event():
    await delivery_store.create("d2", "bucket", "key/d2/video.mp4")
    await delivery_store.append_event("d2", DeliveryEvent(event="detecting", data="..."))

    state = await delivery_store.get("d2")
    assert len(state.events) == 1
    assert state.events[0].event == "detecting"


@pytest.mark.asyncio
async def test_delivery_store_mark_done():
    await delivery_store.create("d3", "bucket", "key/d3/video.mp4")
    await delivery_store.mark_done("d3")

    state = await delivery_store.get("d3")
    assert state.done is True


@pytest.mark.asyncio
async def test_delivery_store_get_returns_none_for_missing():
    result = await delivery_store.get("does-not-exist")
    assert result is None
