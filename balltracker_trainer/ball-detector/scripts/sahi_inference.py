"""SAHI-sliced inference for cricket ball detection.

Slices full-resolution frames into overlapping patches to detect small balls
that would be erased by standard 640px downscaling. Dual purpose:
1. Evaluation on test set with full-resolution accuracy
2. Auto-labeling: generates YOLO .txt labels for unlabeled frames
"""

import argparse
import json
from pathlib import Path

import yaml
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from tqdm import tqdm


def load_sahi_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def prediction_to_yolo_label(prediction, img_width: int, img_height: int) -> str:
    """Convert a SAHI prediction to YOLO format line."""
    bbox = prediction.bbox  # [x_min, y_min, x_max, y_max] in pixels
    x_center = ((bbox.minx + bbox.maxx) / 2) / img_width
    y_center = ((bbox.miny + bbox.maxy) / 2) / img_height
    width = (bbox.maxx - bbox.minx) / img_width
    height = (bbox.maxy - bbox.miny) / img_height
    return f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def main():
    parser = argparse.ArgumentParser(
        description="SAHI-sliced inference for ball detection"
    )
    parser.add_argument(
        "--weights", type=Path, required=True, help="Model weights path"
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="Directory of images"
    )
    parser.add_argument(
        "--sahi-config",
        type=Path,
        default=Path("configs/sahi_config.yaml"),
        help="SAHI config file",
    )
    parser.add_argument(
        "--output-labels",
        type=Path,
        default=None,
        help="Output directory for YOLO .txt labels (auto-labeling mode)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output JSON file with all detections",
    )
    parser.add_argument("--device", type=str, default="auto", help="Device")
    args = parser.parse_args()

    sahi_cfg = load_sahi_config(args.sahi_config)

    device = args.device
    if device == "auto":
        import torch
        if torch.cuda.is_available():
            device = "cuda:0"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    detection_model = AutoDetectionModel.from_pretrained(
        model_type="yolov8",  # SAHI uses yolov8 type for ultralytics models
        model_path=str(args.weights),
        confidence_threshold=sahi_cfg.get("confidence_threshold", 0.25),
        device=device,
    )

    images = sorted(
        list(args.source.glob("*.jpg"))
        + list(args.source.glob("*.jpeg"))
        + list(args.source.glob("*.png"))
    )
    if not images:
        print(f"No images found in {args.source}")
        return

    if args.output_labels:
        args.output_labels.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_detections = 0

    print(f"Running SAHI inference on {len(images)} images...")
    print(f"  Slice size: {sahi_cfg['slice_width']}×{sahi_cfg['slice_height']}")
    print(f"  Overlap: {sahi_cfg['overlap_width_ratio']}")

    for img_path in tqdm(images):
        result = get_sliced_prediction(
            str(img_path),
            detection_model,
            slice_height=sahi_cfg["slice_height"],
            slice_width=sahi_cfg["slice_width"],
            overlap_height_ratio=sahi_cfg["overlap_height_ratio"],
            overlap_width_ratio=sahi_cfg["overlap_width_ratio"],
            postprocess_type=sahi_cfg.get("postprocess_type", "NMS"),
            postprocess_match_metric=sahi_cfg.get("postprocess_match_metric", "IOS"),
            postprocess_match_threshold=sahi_cfg.get("postprocess_match_threshold", 0.5),
            verbose=0,
        )

        detections = result.object_prediction_list
        total_detections += len(detections)

        # Write YOLO labels if requested
        if args.output_labels:
            import cv2
            img = cv2.imread(str(img_path))
            h, w = img.shape[:2]
            label_path = args.output_labels / f"{img_path.stem}.txt"
            with open(label_path, "w") as f:
                for pred in detections:
                    f.write(prediction_to_yolo_label(pred, w, h) + "\n")

        # Collect for JSON output
        if args.output_json:
            all_results.append({
                "image": img_path.name,
                "detections": [
                    {
                        "bbox": [pred.bbox.minx, pred.bbox.miny, pred.bbox.maxx, pred.bbox.maxy],
                        "score": pred.score.value,
                        "category": pred.category.name,
                    }
                    for pred in detections
                ],
            })

    print(f"\nTotal detections: {total_detections} across {len(images)} images")
    print(f"Average: {total_detections / len(images):.1f} detections/image")

    if args.output_labels:
        print(f"Labels saved to: {args.output_labels}")
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"JSON results saved to: {args.output_json}")


if __name__ == "__main__":
    main()
