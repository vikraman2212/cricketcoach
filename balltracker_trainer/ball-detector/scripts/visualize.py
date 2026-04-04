"""Visualize ball detections and trajectories on images or video."""

import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def draw_detection(frame: np.ndarray, box, conf: float) -> None:
    """Draw a detection box with confidence."""
    x1, y1, x2, y2 = [int(v) for v in box]
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    label = f"ball {conf:.2f}"
    cv2.putText(
        frame, label, (x1, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Visualize ball detection predictions"
    )
    parser.add_argument(
        "--weights", type=Path, required=True, help="Model weights path"
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="Image, video, or directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/visualize"),
        help="Output directory",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(args.weights))

    if args.source.is_dir():
        images = sorted(
            list(args.source.glob("*.jpg"))
            + list(args.source.glob("*.png"))
        )
        for img_path in images:
            frame = cv2.imread(str(img_path))
            results = model(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)
            if results[0].boxes is not None:
                for box, conf_val in zip(
                    results[0].boxes.xyxy.cpu().numpy(),
                    results[0].boxes.conf.cpu().numpy(),
                ):
                    draw_detection(frame, box, conf_val)
            out_path = args.output_dir / f"vis_{img_path.name}"
            cv2.imwrite(str(out_path), frame)
            print(f"Saved: {out_path}")

    elif args.source.suffix in (".mp4", ".mov", ".avi"):
        cap = cv2.VideoCapture(str(args.source))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        out_path = args.output_dir / f"vis_{args.source.stem}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            results = model(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)
            if results[0].boxes is not None:
                for box, conf_val in zip(
                    results[0].boxes.xyxy.cpu().numpy(),
                    results[0].boxes.conf.cpu().numpy(),
                ):
                    draw_detection(frame, box, conf_val)
            writer.write(frame)

        cap.release()
        writer.release()
        print(f"Saved: {out_path}")

    else:
        frame = cv2.imread(str(args.source))
        results = model(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)
        if results[0].boxes is not None:
            for box, conf_val in zip(
                results[0].boxes.xyxy.cpu().numpy(),
                results[0].boxes.conf.cpu().numpy(),
            ):
                draw_detection(frame, box, conf_val)
        out_path = args.output_dir / f"vis_{args.source.name}"
        cv2.imwrite(str(out_path), frame)
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
