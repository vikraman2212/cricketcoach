"""Export trained YOLOv11 ball detection model to ONNX or TensorRT."""

import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Export ball detection model")
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="Path to trained model weights (best.pt)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="onnx",
        choices=["onnx", "torchscript", "engine"],
        help="Export format (default: onnx)",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument(
        "--half", action="store_true", help="FP16 quantization (GPU only)"
    )
    parser.add_argument(
        "--dynamic", action="store_true", help="Dynamic input shapes (ONNX)"
    )
    args = parser.parse_args()

    model = YOLO(str(args.weights))

    export_path = model.export(
        format=args.format,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
    )

    print(f"\nExported to: {export_path}")

    if args.format == "onnx":
        print("Validating exported ONNX model...")
        exported_model = YOLO(export_path)
        print("Validation successful — model loads correctly.")


if __name__ == "__main__":
    main()
