from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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