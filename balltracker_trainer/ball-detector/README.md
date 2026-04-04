# ball-detector

Fine-tune YOLOv11 for cricket ball detection with SAHI slicing and ByteTrack tracking.

## Problem

Standard YOLO downscales images to 640×640, completely erasing a 7cm cricket ball shot from 20 meters away. Additional challenges:

- **Small object size** — the ball occupies <0.1% of a 1080p frame at typical camera distances
- **High-speed motion blur** — the ball becomes a streak at 120+ km/h
- **False positives** — red shoes, cones, and boundary rope markers trigger detections
- **Occlusion** — the ball disappears behind the bat, batsman, or stumps mid-trajectory

## Solution

- **SAHI** (Slicing Aided Hyper Inference) — slices the 1080p frame into overlapping 320×320 squares to detect the ball before downscaling
- **ByteTrack + Kalman Filter** — predicts ball coordinates during occluded frames so speed calculations don't break
- **Red distractor training** — dataset intentionally includes red distractions to reduce false positives

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Prepare dataset (extract frames from videos)
python data/prepare_dataset.py --video-dir /path/to/videos --fps 30

# Validate annotations
python data/validate_annotations.py --labels-dir datasets/cricket-ball/labels/train

# Train
python scripts/train.py --config configs/training_config.yaml

# Evaluate
python scripts/evaluate.py --weights runs/detect/train/weights/best.pt

# SAHI inference (sliced prediction on full-res frames)
python scripts/sahi_inference.py --weights runs/detect/train/weights/best.pt --source /path/to/frames

# ByteTrack demo (tracking on video)
python scripts/track_demo.py --weights runs/detect/train/weights/best.pt --video /path/to/video.mp4

# Export
python scripts/export_model.py --weights runs/detect/train/weights/best.pt --format onnx

# Visualize
python scripts/visualize.py --weights runs/detect/train/weights/best.pt --source /path/to/image_or_video
```

## Dataset Structure

```
datasets/cricket-ball/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

Label format (YOLO `.txt`): `class x_center y_center width height`

See [data/README.md](data/README.md) for dataset collection guidelines.
