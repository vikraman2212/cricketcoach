"""Train YOLOv11-Pose on the cricket bowling dataset.

Loads hyperparameters from configs/training_config.yaml.
CLI arguments override config values.
"""

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv11-Pose for bowling")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/training_config.yaml"),
        help="Training config file",
    )
    # Allow CLI overrides for common params
    parser.add_argument("--model", type=str, help="Pre-trained model path")
    parser.add_argument("--data", type=str, help="Dataset config path")
    parser.add_argument("--epochs", type=int, help="Number of epochs")
    parser.add_argument("--batch", type=int, help="Batch size")
    parser.add_argument("--imgsz", type=int, help="Image size")
    parser.add_argument("--device", type=str, help="Device (auto, 0, cpu, mps)")
    parser.add_argument("--resume", type=str, help="Resume from checkpoint")
    args = parser.parse_args()

    config = load_config(args.config)

    # CLI overrides
    for key in ["model", "data", "epochs", "batch", "imgsz", "device"]:
        cli_val = getattr(args, key, None)
        if cli_val is not None:
            config[key] = cli_val

    model_name = config.pop("model")
    model = YOLO(model_name)

    if args.resume:
        config["resume"] = args.resume

    print(f"Training {model_name} with config:")
    for k, v in sorted(config.items()):
        print(f"  {k}: {v}")
    print()

    results = model.train(**config)
    print(f"\nTraining complete. Best weights: {results.save_dir}/weights/best.pt")


if __name__ == "__main__":
    main()
