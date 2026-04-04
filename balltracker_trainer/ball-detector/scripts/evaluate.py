"""Evaluate a trained YOLOv11 ball detection model.

Reports mAP@50, mAP@50-95 with focus on small-object recall.
"""

import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Evaluate ball detection model")
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="Path to trained model weights (best.pt)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("configs/cricket_ball.yaml"),
        help="Dataset config",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--device", type=str, default="auto", help="Device")
    args = parser.parse_args()

    model = YOLO(str(args.weights))
    results = model.val(data=str(args.data), imgsz=args.imgsz, device=args.device)

    print(f"\n{'='*60}")
    print("Detection Metrics:")
    print(f"  mAP@50:    {results.box.map50:.4f}")
    print(f"  mAP@50-95: {results.box.map:.4f}")
    print(f"  Precision: {results.box.mp:.4f}")
    print(f"  Recall:    {results.box.mr:.4f}")
    print(f"\nResults saved to: {results.save_dir}")
    print(
        "\nNote: For full-resolution evaluation with SAHI slicing, "
        "use scripts/sahi_inference.py instead."
    )


if __name__ == "__main__":
    main()
