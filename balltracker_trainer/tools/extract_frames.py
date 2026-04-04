"""Extract frames from downloaded videos for ML training.

Unified extractor for both ball-detector and bowler-pose projects.
Writes metadata sidecar JSON per frame for provenance tracking.
"""

import argparse
import json
import random
import shutil
from pathlib import Path

import cv2
import yaml
from tqdm import tqdm


def find_video_metadata(video_path: Path, catalog_path: Path | None) -> dict:
    """Look up metadata for a video from the catalog by matching filename."""
    if catalog_path is None or not catalog_path.exists():
        return {}

    with open(catalog_path) as f:
        catalog = yaml.safe_load(f)

    stem = video_path.stem.lower()
    for entry in catalog.get("videos", []):
        # Match by bowler name or URL ID in filename
        bowler = entry.get("bowler_name", "").lower()
        if bowler and bowler in stem:
            return entry
    return {}


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: int,
    fmt: str,
    metadata: dict,
) -> list[Path]:
    """Extract frames from a single video at the specified FPS."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Warning: could not open {video_path}")
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(video_fps / fps))
    stem = video_path.stem
    ext = "png" if fmt == "png" else "jpg"

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            out_path = output_dir / f"{stem}_frame{frame_idx:06d}.{ext}"
            if fmt == "png":
                cv2.imwrite(str(out_path), frame)
            else:
                cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            extracted.append(out_path)

            # Write sidecar metadata JSON
            sidecar = {
                "source_video": video_path.name,
                "frame_index": frame_idx,
                "timestamp_sec": round(frame_idx / video_fps, 3),
                "ball_color": metadata.get("ball_color", "unknown"),
                "bowling_style": metadata.get("bowling_style", "unknown"),
                "camera_angle": metadata.get("camera_angle", "unknown"),
                "laterality": metadata.get("laterality", "unknown"),
            }
            sidecar_path = out_path.with_suffix(".json")
            with open(sidecar_path, "w") as f:
                json.dump(sidecar, f, indent=2)

        frame_idx += 1

    cap.release()
    return extracted


def split_dataset(
    frames: list[Path],
    dest_dir: Path,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> None:
    """Split frames into train/val directories, copying sidecar JSONs too."""
    random.seed(seed)
    shuffled = list(frames)
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * (1 - val_ratio))
    train_frames = shuffled[:split_idx]
    val_frames = shuffled[split_idx:]

    train_dir = dest_dir / "images" / "train"
    val_dir = dest_dir / "images" / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    for f in tqdm(train_frames, desc="Copying train"):
        shutil.copy2(f, train_dir / f.name)
        sidecar = f.with_suffix(".json")
        if sidecar.exists():
            shutil.copy2(sidecar, train_dir / sidecar.name)

    for f in tqdm(val_frames, desc="Copying val"):
        shutil.copy2(f, val_dir / f.name)
        sidecar = f.with_suffix(".json")
        if sidecar.exists():
            shutil.copy2(sidecar, val_dir / sidecar.name)

    print(f"Train: {len(train_frames)} frames, Val: {len(val_frames)} frames")


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from cricket videos for ML training"
    )
    parser.add_argument(
        "--video-dir",
        type=Path,
        required=True,
        help="Directory containing downloaded video files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for extracted frames",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Extraction FPS (30 for ball-detector, 5 for pose)",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["png", "jpg"],
        default="png",
        help="Output format (png=lossless for ball, jpg for pose)",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).parent / "video_catalog.yaml",
        help="Video catalog for metadata lookup",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Split into train/val after extraction",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for split"
    )
    args = parser.parse_args()

    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
    videos = [
        f
        for f in sorted(args.video_dir.iterdir())
        if f.suffix.lower() in video_extensions
    ]

    if not videos:
        print(f"No video files found in {args.video_dir}")
        return

    print(f"Found {len(videos)} videos, extracting at {args.fps} FPS ({args.fmt})")

    temp_dir = args.output_dir / "_extracted_temp"
    all_frames: list[Path] = []

    for video in videos:
        metadata = find_video_metadata(video, args.catalog)
        frames = extract_frames(video, temp_dir, args.fps, args.fmt, metadata)
        all_frames.extend(frames)
        print(f"  {video.name}: {len(frames)} frames")

    print(f"\nTotal: {len(all_frames)} frames extracted")

    if args.split:
        split_dataset(all_frames, args.output_dir, args.val_ratio, args.seed)
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        # Move frames from temp to output root
        final_dir = args.output_dir / "images"
        final_dir.mkdir(parents=True, exist_ok=True)
        for f in all_frames:
            shutil.move(str(f), str(final_dir / f.name))
            sidecar = f.with_suffix(".json")
            if sidecar.exists():
                shutil.move(str(sidecar), str(final_dir / sidecar.name))
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Frames saved to {final_dir}")


if __name__ == "__main__":
    main()
