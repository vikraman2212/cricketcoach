from uuid import uuid4

from .config import load_default_inference_config
from .schemas import (
    AnalyzeDeliveryConfig,
    AnalyzeDeliveryResponse,
    Biomechanics,
    DeliveryPhysics,
    Deviation,
    SystemEvaluations,
)


class BootstrapAnalysisService:
    def __init__(self) -> None:
        self.default_config = load_default_inference_config()

    def analyze(
        self,
        video_name: str,
        video_bytes: bytes,
        config: AnalyzeDeliveryConfig,
    ) -> AnalyzeDeliveryResponse:
        bowling_style = config.bowling_style.lower()

        if "spin" in bowling_style:
            speed_kmh = 78.5
            pitch_length = "full"
            swing_type = "drift"
            swing_degrees = 1.4
            approach_velocity_mps = 3.9
            front_knee_angle_degrees = 158.0
            momentum_transfer_efficiency = 0.68
            strengths = [
                "Good control through the crease for a spin release",
                "Stable front side at landing",
            ]
            flaws = [
                "Needs more drift or dip signal from the tracked flight path",
                "Run-up momentum is currently limited for power generation",
            ]
        elif "medium" in bowling_style:
            speed_kmh = 94.2
            pitch_length = "good"
            swing_type = "seam"
            swing_degrees = 1.2
            approach_velocity_mps = 5.1
            front_knee_angle_degrees = 151.0
            momentum_transfer_efficiency = 0.72
            strengths = [
                "Balanced approach speed into the crease",
                "Repeatable release profile for line and length work",
            ]
            flaws = [
                "Front knee can brace harder to convert more momentum into pace",
                "Limited lateral movement in the current delivery profile",
            ]
        else:
            speed_kmh = 118.4
            pitch_length = "short"
            swing_type = "inswing" if "left" in bowling_style else "outswing"
            swing_degrees = 2.1
            approach_velocity_mps = 6.8
            front_knee_angle_degrees = 145.0
            momentum_transfer_efficiency = 0.75
            strengths = [
                "Excellent approach velocity into the crease",
                f"Useful natural {swing_type} shape through the air",
            ]
            flaws = [
                "Front knee is collapsing at release and leaking pace",
                "Landing alignment still needs tightening for repeatability",
            ]

        speed_kmh += round((config.bowler_height_cm - 175) * 0.08, 1)
        approach_velocity_mps += round((config.bowler_height_cm - 175) * 0.01, 1)
        if config.ball_weight_grams >= 156:
            speed_kmh += 0.4

        if len(video_bytes) == 0:
            raise ValueError("Uploaded video is empty")

        return AnalyzeDeliveryResponse(
            delivery_id=str(uuid4()),
            delivery_physics=DeliveryPhysics(
                speed_kmh=round(speed_kmh, 1),
                pitch_length=pitch_length,
                deviation=Deviation(
                    swing_type=swing_type,
                    swing_degrees=round(swing_degrees, 1),
                ),
            ),
            biomechanics=Biomechanics(
                approach_velocity_mps=round(approach_velocity_mps, 1),
                front_knee_angle_degrees=round(front_knee_angle_degrees, 1),
                momentum_transfer_efficiency=round(momentum_transfer_efficiency, 2),
            ),
            system_evaluations=SystemEvaluations(
                identified_strengths=[
                    *strengths,
                    f"Bootstrap analysis generated from {video_name}",
                ],
                identified_flaws=flaws,
            ),
        )