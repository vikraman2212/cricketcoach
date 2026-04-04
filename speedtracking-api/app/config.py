from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


class ServiceSettings(BaseModel):
    app_name: str = "speedtracking-api"
    analysis_mode: str = "bootstrap"
    default_inference_config_path: Path = (
        Path(__file__).resolve().parents[2]
        / "balltracker_trainer"
        / "ball-detector"
        / "configs"
        / "inference_config.yaml"
    )


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()


def load_default_inference_config() -> dict:
    settings = get_settings()
    if not settings.default_inference_config_path.exists():
        return {}

    with open(settings.default_inference_config_path) as file:
        data = yaml.safe_load(file) or {}
    return data