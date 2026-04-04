# bowler-pose

Fine-tune YOLOv11-Pose for cricket bowling biomechanics.

## Problem

Off-the-shelf pose estimation models (COCO-trained) fail on fast bowling due to:

- **Extreme hyperextension** — shoulders/elbows bend in ways generic models classify as "impossible"
- **Severe occlusion** — bowling arm disappears behind head/torso during load-up
- **High-speed motion blur** — wrist and fingers become a blur at 120+ km/h

## Solution

Transfer learning: take pre-trained `yolo11s-pose.pt` weights and fine-tune exclusively on 3,000–5,000 annotated frames of cricket bowling actions.

## 17-Keypoint Map (COCO format)

```
 0: Nose          1: L-Eye        2: R-Eye        3: L-Ear        4: R-Ear
 5: L-Shoulder    6: R-Shoulder   7: L-Elbow      8: R-Elbow
 9: L-Wrist      10: R-Wrist
11: L-Hip        12: R-Hip       13: L-Knee      14: R-Knee
15: L-Ankle      16: R-Ankle
```

**Critical physics nodes:** 5–10 (upper body rotation & release angle), 11–16 (crease momentum & knee brace).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Prepare dataset (extract frames from videos)
python data/prepare_dataset.py --video-dir /path/to/videos --fps 5

# Validate annotations
python data/validate_annotations.py --labels-dir datasets/cricket-pose/labels/train

# Train
python scripts/train.py --config configs/training_config.yaml

# Evaluate
python scripts/evaluate.py --weights runs/pose/train/weights/best.pt

# Auto-label (bootstrap unlabeled frames)
python scripts/auto_label.py --model runs/pose/train/weights/best.pt --source /path/to/unlabeled

# Export
python scripts/export_model.py --weights runs/pose/train/weights/best.pt --format onnx

# Visualize
python scripts/visualize.py --weights runs/pose/train/weights/best.pt --source /path/to/image_or_video
```

## Dataset Structure

```
datasets/cricket-pose/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

Label format (YOLO-Pose `.txt`): `class x_center y_center width height kp0_x kp0_y kp0_v kp1_x kp1_y kp1_v ... kp16_x kp16_y kp16_v`

See [data/README.md](data/README.md) for annotation guidelines.
