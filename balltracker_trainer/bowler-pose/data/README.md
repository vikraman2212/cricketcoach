# Annotation Guidelines for bowler-pose

## Keypoint Format

Each annotation is a YOLO-Pose `.txt` file with one line per detected bowler:

```
class x_center y_center width height kp0_x kp0_y kp0_v kp1_x kp1_y kp1_v ... kp16_x kp16_y kp16_v
```

- **class**: Always `0` (bowler)
- **bbox**: Normalized coordinates `[0, 1]`
- **keypoints**: 17 × 3 values (x, y, visibility)

## Visibility Flags

| Flag | Meaning          | When to Use                                                    |
| ---- | ---------------- | -------------------------------------------------------------- |
| `2`  | **Visible**      | Joint is clearly seen in the frame                             |
| `1`  | **Occluded**     | Joint is hidden behind the body/head, but you know where it is |
| `0`  | **Not in image** | Joint is off-camera or truly impossible to estimate            |

### Critical Rule for Bowling

**When the bowling arm disappears behind the back during load-up, do NOT leave it blank.**

You must use human intuition to place the keypoint where the elbow/wrist technically is, and set the flag to `1` (Occluded). This trains the neural network to mathematically infer joint locations based on visible body parts (shoulders and hips).

## Dataset Variance Requirements

To prevent overfitting to one type of player, the dataset must contain **3,000–5,000 annotated frames** with extreme variance:

### 1. Action Types

- Traditional side-on (e.g., Pat Cummins)
- Front-on / chest-on (e.g., Makhaya Ntini)
- Slingers (e.g., Lasith Malinga)
- Extreme hyperextension (e.g., Jasprit Bumrah)

### 2. Laterality

- 50% right-arm bowlers
- 50% left-arm bowlers

### 3. Camera Angles

- **Strictly** "Behind the Stumps" or "Umpire POV" angles
- **Do NOT** include square-leg (side-on) camera angles — this confuses the depth perception matrix

### 4. Lighting & Apparel

- Mix white clothing (Test match style) with colored T20 kits
- Prevents the model from assuming "white sleeves = arms"

## Auto-Labeling Workflow

1. Manually label **300** highly diverse frames in CVAT/Roboflow
2. Train a base `yolo11n-pose` model for **50 epochs**
3. Run inference on the remaining ~4,000 frames to auto-generate `.txt` files
4. Import back into CVAT and **manually correct the hallucinated joints**

Use `scripts/auto_label.py` for step 3.

## Validation

Run the annotation validator to check your labels:

```bash
python data/validate_annotations.py --labels-dir datasets/cricket-pose/labels/train
```
