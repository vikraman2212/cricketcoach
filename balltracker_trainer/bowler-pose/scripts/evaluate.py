"""Evaluate a trained YOLOv11-Pose model.

Reports mAP@50, mAP@50-95, and per-keypoint metrics.
"""

import argparse
from pathlib import Path

from ultralytics import YOLO

KEYPOINT_NAMES = [
    "Nose", "L-Eye", "R-Eye", "L-Ear", "R-Ear",
    "L-Shoulder", "R-Shoulder", "L-Elbow", "R-Elbow",
    "L-Wrist", "R-Wrist",
    "L-Hip", "R-Hip", "L-Knee", "R-Knee",
    "L-Ankle", "R-Ankle",
]

CRITICAL_NODES = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained pose model")
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="Path to trained model weights (best.pt)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("configs/cricket_pose.yaml"),
        help="Dataset config",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--device", type=str, default="auto", help="Device")
    args = parser.parse_args()

    model = YOLO(str(args.weights))
    results = model.val(data=str(args.data), imgsz=args.imgsz, device=args.device)

    print(f"\n{'='*60}")
    print("Overall Metrics:")
    print(f"  mAP@50:    {results.box.map50:.4f}")
    print(f"  mAP@50-95: {results.box.map:.4f}")

    if hasattr(results, "pose"):
        print(f"\nPose Metrics:")
        print(f"  Pose mAP@50:    {results.pose.map50:.4f}")
        print(f"  Pose mAP@50-95: {results.pose.map:.4f}")

    print(f"\nResults saved to: {results.save_dir}")


if __name__ == "__main__":
    main()
