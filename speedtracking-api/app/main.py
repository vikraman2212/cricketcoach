import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .config import get_settings, load_default_inference_config
from .schemas import AnalyzeDeliveryConfig, AnalyzeDeliveryResponse
from .services import BootstrapAnalysisService

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