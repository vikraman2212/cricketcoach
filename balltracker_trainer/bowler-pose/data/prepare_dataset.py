"""Extract frames from bowling videos and split into train/val sets."""

import argparse
import random
import shutil
from pathlib import Path

import cv2
from tqdm import tqdm


def extract_frames(video_path: Path, output_dir: Path, fps: int) -> list[Path]:
    """Extract frames from a video at the specified FPS."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Warning: could not open {video_path}")
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(video_fps / fps))
    stem = video_path.stem

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            out_path = output_dir / f"{stem}_frame{frame_idx:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            extracted.append(out_path)
        frame_idx += 1

    cap.release()
    return extracted


def split_dataset(
    frames: list[Path], dest_dir: Path, val_ratio: float = 0.2, seed: int = 42
) -> None:
    """Split extracted frames into train/val directories."""
    random.seed(seed)
    random.shuffle(frames)

    split_idx = int(len(frames) * (1 - val_ratio))
    train_frames = frames[:split_idx]
    val_frames = frames[split_idx:]

    train_dir = dest_dir / "images" / "train"
    val_dir = dest_dir / "images" / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    for f in tqdm(train_frames, desc="Copying train"):
        shutil.copy2(f, train_dir / f.name)
    for f in tqdm(val_frames, desc="Copying val"):
        shutil.copy2(f, val_dir / f.name)

    print(f"Train: {len(train_frames)} frames, Val: {len(val_frames)} frames")


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from bowling videos for pose dataset"
    )
    parser.add_argument(
        "--video-dir", type=Path, required=True, help="Directory containing .mp4 videos"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("datasets/cricket-pose"),
        help="Output dataset directory (default: datasets/cricket-pose)",
    )
    parser.add_argument(
        "--fps", type=int, default=5, help="Frames per second to extract (default: 5)"
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Fraction of frames for validation (default: 0.2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for split (default: 42)"
    )
    args = parser.parse_args()

    video_files = sorted(args.video_dir.glob("*.mp4"))
    if not video_files:
        print(f"No .mp4 files found in {args.video_dir}")
        return

    print(f"Found {len(video_files)} videos")

    tmp_dir = args.output_dir / "_extracted_tmp"
    all_frames = []
    for video in tqdm(video_files, desc="Extracting"):
        frames = extract_frames(video, tmp_dir, args.fps)
        all_frames.extend(frames)

    print(f"Extracted {len(all_frames)} total frames")
    split_dataset(all_frames, args.output_dir, args.val_ratio, args.seed)

    shutil.rmtree(tmp_dir)
    print("Done.")


if __name__ == "__main__":
    main()
