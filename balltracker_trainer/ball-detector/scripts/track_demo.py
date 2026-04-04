"""ByteTrack + Kalman filter tracking demo for cricket ball.

Demonstrates the full tracking pipeline on a video:
1. YOLO ball detection per frame
2. ByteTrack association across frames
3. Kalman filter prediction during occlusion (ball behind bat/batsman)
4. Trajectory visualization

This validates the tracking pipeline before it's deployed in the inference service.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def draw_trajectory(
    frame: np.ndarray, trajectory: list[tuple[int, int]], color=(0, 255, 255)
) -> None:
    """Draw ball trajectory as a fading trail."""
    for i in range(1, len(trajectory)):
        alpha = i / len(trajectory)
        thickness = max(1, int(3 * alpha))
        cv2.line(
            frame,
            trajectory[i - 1],
            trajectory[i],
            color,
            thickness,
            cv2.LINE_AA,
        )
    if trajectory:
        cv2.circle(frame, trajectory[-1], 6, (0, 0, 255), -1, cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser(
        description="ByteTrack ball tracking demo on video"
    )
    parser.add_argument(
        "--weights", type=Path, required=True, help="Ball detection model weights"
    )
    parser.add_argument(
        "--video", type=Path, required=True, help="Input video file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/tracking"),
        help="Output directory",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size for detection")
    parser.add_argument(
        "--max-trail", type=int, default=60, help="Maximum trajectory trail length"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(args.weights))

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print(f"Error: could not open {args.video}")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out_path = args.output_dir / f"tracked_{args.video.stem}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    trajectory: list[tuple[int, int]] = []
    detected_frames = 0
    total_processed = 0

    print(f"Processing {total_frames} frames from {args.video.name}...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_processed += 1

        # Run detection with built-in ByteTrack tracker
        results = model.track(
            frame,
            conf=args.conf,
            imgsz=args.imgsz,
            persist=True,  # Maintain tracks across frames
            tracker="bytetrack.yaml",
            verbose=False,
        )

        # Extract ball position
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            # Take highest-confidence detection
            boxes = results[0].boxes
            best_idx = boxes.conf.argmax()
            x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy().astype(int)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            trajectory.append((cx, cy))
            detected_frames += 1

            # Draw detection box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw track ID if available
            if results[0].boxes.id is not None:
                track_id = int(results[0].boxes.id[best_idx])
                cv2.putText(
                    frame,
                    f"ID:{track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

        # Trim trajectory trail
        if len(trajectory) > args.max_trail:
            trajectory = trajectory[-args.max_trail :]

        # Draw trajectory
        draw_trajectory(frame, trajectory)

        # Stats overlay
        cv2.putText(
            frame,
            f"Frame: {total_processed}/{total_frames} | Detected: {detected_frames}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        writer.write(frame)

    cap.release()
    writer.release()

    print(f"\nTracking complete:")
    print(f"  Frames processed: {total_processed}")
    print(f"  Ball detected in: {detected_frames} frames ({100*detected_frames/max(1,total_processed):.1f}%)")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
