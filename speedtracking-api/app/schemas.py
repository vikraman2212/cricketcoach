from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── MinIO webhook payload ─────────────────────────────────────────────────────


class MinioS3Object(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str


class MinioS3Bucket(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str


class MinioS3Detail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bucket: MinioS3Bucket
    object: MinioS3Object


class MinioRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    s3: MinioS3Detail


class MinioWebhookPayload(BaseModel):
    """Payload sent by MinIO for s3:ObjectCreated:Put events."""

    model_config = ConfigDict(extra="ignore")

    EventName: str
    Key: str
    Records: list[MinioRecord] = Field(default_factory=list)

    def bucket(self) -> str:
        if self.Records:
            return self.Records[0].s3.bucket.name
        return self.Key.split("/")[0]

    def object_key(self) -> str:
        if self.Records:
            return self.Records[0].s3.object.key
        parts = self.Key.split("/", 1)
        return parts[1] if len(parts) > 1 else self.Key


# ── Delivery pipeline ─────────────────────────────────────────────────────────


class DeliveryEventPayload(BaseModel):
    event: str
    data: Any


# ── Analysis config & response ────────────────────────────────────────────────


class AnalyzeDeliveryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pitch_length_meters: float = Field(gt=0)
    ball_color: Literal["red", "white", "pink"]
    ball_weight_grams: int = Field(gt=0)
    bowling_style: str = Field(min_length=3)
    bowler_height_cm: int = Field(gt=0)


class Deviation(BaseModel):
    swing_type: str
    swing_degrees: float


class DeliveryPhysics(BaseModel):
    speed_kmh: float
    pitch_length: str
    deviation: Deviation


class Biomechanics(BaseModel):
    approach_velocity_mps: float
    front_knee_angle_degrees: float
    momentum_transfer_efficiency: float


class SystemEvaluations(BaseModel):
    identified_strengths: list[str]
    identified_flaws: list[str]


class AnalyzeDeliveryResponse(BaseModel):
    delivery_id: str
    delivery_physics: DeliveryPhysics
    biomechanics: Biomechanics
    system_evaluations: SystemEvaluations