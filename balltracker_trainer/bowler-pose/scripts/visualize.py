"""Visualize YOLOv11-Pose predictions with skeleton overlays.

Highlights critical physics nodes in distinct colors:
- Nodes 5-10 (upper body): cyan — release angle & rotation
- Nodes 11-16 (lower body): magenta — crease momentum & knee brace
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# Color scheme for critical physics nodes
UPPER_BODY_COLOR = (255, 255, 0)   # Cyan (BGR) — nodes 5-10
LOWER_BODY_COLOR = (255, 0, 255)   # Magenta (BGR) — nodes 11-16
DEFAULT_COLOR = (0, 255, 0)        # Green — nodes 0-4

SKELETON = [
    (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
    (5, 11), (6, 12), (5, 6), (5, 7), (6, 8),
    (7, 9), (8, 10), (1, 2), (0, 1), (0, 2),
    (1, 3), (2, 4), (3, 5), (4, 6),
]


def get_node_color(kp_idx: int) -> tuple:
    if 5 <= kp_idx <= 10:
        return UPPER_BODY_COLOR
    elif 11 <= kp_idx <= 16:
        return LOWER_BODY_COLOR
    return DEFAULT_COLOR


def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray, conf_thresh: float = 0.3):
    """Draw skeleton on a frame with physics-node color coding."""
    h, w = frame.shape[:2]

    # Draw bones
    for p1, p2 in SKELETON:
        x1, y1, c1 = keypoints[p1]
        x2, y2, c2 = keypoints[p2]
        if c1 > conf_thresh and c2 > conf_thresh:
            pt1 = (int(x1), int(y1))
            pt2 = (int(x2), int(y2))
            color = get_node_color(p1)
            cv2.line(frame, pt1, pt2, color, 2, cv2.LINE_AA)

    # Draw joints
    for idx, (x, y, conf) in enumerate(keypoints):
        if conf > conf_thresh:
            color = get_node_color(idx)
            radius = 5 if 5 <= idx <= 16 else 3
            cv2.circle(frame, (int(x), int(y)), radius, color, -1, cv2.LINE_AA)

    return frame


def process_image(model: YOLO, img_path: Path, output_dir: Path, conf: float):
    results = model(str(img_path), conf=conf, verbose=False)
    frame = cv2.imread(str(img_path))

    if results[0].keypoints is not None:
        for kps in results[0].keypoints.data.cpu().numpy():
            draw_skeleton(frame, kps)

    out_path = output_dir / f"vis_{img_path.name}"
    cv2.imwrite(str(out_path), frame)
    return out_path


def process_video(model: YOLO, video_path: Path, output_dir: Path, conf: float):
    cap = cv2.VideoCapture(str(video_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    out_path = output_dir / f"vis_{video_path.stem}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Processing {frame_count} frames...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=conf, verbose=False)
        if results[0].keypoints is not None:
            for kps in results[0].keypoints.data.cpu().numpy():
                draw_skeleton(frame, kps)

        writer.write(frame)

    cap.release()
    writer.release()
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Visualize pose predictions with skeleton overlays"
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
    parser.add_argument("--conf", type=float, default=0.3, help="Confidence threshold")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(args.weights))

    if args.source.is_dir():
        images = sorted(
            list(args.source.glob("*.jpg"))
            + list(args.source.glob("*.png"))
        )
        for img in images:
            out = process_image(model, img, args.output_dir, args.conf)
            print(f"Saved: {out}")
    elif args.source.suffix in (".mp4", ".mov", ".avi"):
        out = process_video(model, args.source, args.output_dir, args.conf)
        print(f"Saved: {out}")
    else:
        out = process_image(model, args.source, args.output_dir, args.conf)
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
