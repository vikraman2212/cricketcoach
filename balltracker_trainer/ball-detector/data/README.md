# Dataset Guidelines for ball-detector

## Annotation Format

Each annotation is a YOLO `.txt` file with one line per detected ball:

```
class x_center y_center width height
```

- **class**: Always `0` (cricket_ball)
- **bbox**: Normalized coordinates `[0, 1]`
- Ball bboxes should be very small — typically < 1% of frame area

## Critical Dataset Requirements

### 1. Red Distractor Inclusion

**YOLO will trigger false positives on red objects.** The dataset MUST intentionally include:

- Red shoes (batting/bowling)
- Boundary rope and markers
- Red cones on the field
- Red logos on clothing
- Red stumps/bails

Annotate these frames with **only the ball labeled** — the red distractors should be present but unlabeled, teaching the model to distinguish ball from non-ball red objects.

### 2. Ball Color Variance

Include all ball types used in cricket:

- **Red** (Test matches)
- **White** (ODI/T20)
- **Pink** (Day-Night Tests)

### 3. Ball Size Variance

The ball appears at different apparent sizes depending on camera distance:

- Close-up shots (ball fills ~2-3% of frame)
- Mid-range (ball at ~0.5% of frame)
- Far shots (ball at <0.1% of frame — this is why SAHI matters)

### 4. Motion Blur Frames

Include frames where the ball is visibly blurred from speed. These are the hardest frames to detect but the most important for continuous tracking.

### 5. Camera Angles

- **Primary**: Behind the stumps / Umpire POV
- Must match the app's required recording angle
- Do NOT include side-on broadcast angles

### 6. Lighting Conditions

- Day matches (bright sunlight, harsh shadows)
- Day-Night matches (artificial + natural light)
- Net sessions (indoor/overcast)

## Negative Examples

Include frames where the ball is NOT visible (in the bowler's hand, behind the bat, after crossing boundary) with **empty label files** (0 bytes). This teaches the model when NOT to detect.

## Auto-Labeling with SAHI

Use `scripts/sahi_inference.py` to bootstrap annotations:

```bash
python scripts/sahi_inference.py \
    --weights path/to/partial_model.pt \
    --source /path/to/unlabeled_frames \
    --output-labels /path/to/generated_labels
```

Then import into your annotation tool and manually correct.

## Validation

```bash
python data/validate_annotations.py --labels-dir datasets/cricket-ball/labels/train
```
