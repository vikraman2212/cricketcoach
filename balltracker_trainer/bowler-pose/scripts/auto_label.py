"""Auto-label unlabeled frames using a partially-trained pose model.

Implements the 4-step auto-labeling workflow:
1. (Manual) Label 300 diverse frames in CVAT/Roboflow
2. (Manual) Train base model for 50 epochs
3. (This script) Run inference on remaining unlabeled frames → generate .txt files
4. (Manual) Import into CVAT and correct hallucinated joints
"""

import argparse
from pathlib import Path

from tqdm import tqdm
from ultralytics import YOLO


def write_yolo_pose_label(result, output_path: Path) -> None:
    """Write YOLO-Pose format label from a prediction result."""
    with open(output_path, "w") as f:
        if result.keypoints is None or len(result.boxes) == 0:
            return  # Empty file = no detection

        boxes = result.boxes.xywhn.cpu()  # Normalized xywh
        keypoints = result.keypoints.data.cpu()  # (N, 17, 3)

        for box, kps in zip(boxes, keypoints):
            parts = ["0"]  # class = bowler
            parts.extend(f"{v:.6f}" for v in box)

            for kp in kps:
                x, y, conf = kp
                # Convert confidence to visibility flag
                # High conf → visible (2), medium → occluded (1), low → not visible (0)
                if conf > 0.5:
                    vis = 2
                elif conf > 0.2:
                    vis = 1
                else:
                    vis = 0
                parts.extend([f"{x:.6f}", f"{y:.6f}", str(vis)])

            f.write(" ".join(parts) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-label frames using a partially-trained pose model"
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to partially-trained model weights",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Directory of unlabeled images",
    )
    parser.add_argument(
        "--output-labels",
        type=Path,
        default=None,
        help="Output directory for generated .txt labels (default: alongside images)",
    )
    parser.add_argument(
        "--conf", type=float, default=0.25, help="Confidence threshold"
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--device", type=str, default="auto", help="Device")
    args = parser.parse_args()

    model = YOLO(str(args.model))

    images = sorted(
        list(args.source.glob("*.jpg"))
        + list(args.source.glob("*.jpeg"))
        + list(args.source.glob("*.png"))
    )
    if not images:
        print(f"No images found in {args.source}")
        return

    output_dir = args.output_labels or args.source
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Auto-labeling {len(images)} images...")
    labeled = 0

    for img_path in tqdm(images):
        results = model(
            str(img_path), conf=args.conf, imgsz=args.imgsz, device=args.device,
            verbose=False,
        )
        label_path = output_dir / f"{img_path.stem}.txt"
        write_yolo_pose_label(results[0], label_path)
        if label_path.stat().st_size > 0:
            labeled += 1

    print(f"\nGenerated labels for {labeled}/{len(images)} images")
    print(f"Labels saved to: {output_dir}")
    print("\nNext step: Import into CVAT/Roboflow and manually correct hallucinated joints.")


if __name__ == "__main__":
    main()
