"""Validate YOLO-Pose annotation files for cricket bowling dataset.

Checks:
- Each label has exactly 1 + 4 + 17*3 = 56 values per line
- Class ID is 0 (bowler)
- Bounding box values are normalized [0, 1]
- Visibility flags are in {0, 1, 2}
- Reports statistics on occluded/missing keypoints
"""

import argparse
from pathlib import Path

NUM_KEYPOINTS = 17
VALUES_PER_KP = 3  # x, y, visibility
BBOX_VALUES = 4  # x_center, y_center, width, height
EXPECTED_VALUES = 1 + BBOX_VALUES + (NUM_KEYPOINTS * VALUES_PER_KP)  # 56

KEYPOINT_NAMES = [
    "Nose", "L-Eye", "R-Eye", "L-Ear", "R-Ear",
    "L-Shoulder", "R-Shoulder", "L-Elbow", "R-Elbow",
    "L-Wrist", "R-Wrist",
    "L-Hip", "R-Hip", "L-Knee", "R-Knee",
    "L-Ankle", "R-Ankle",
]

CRITICAL_NODES = {5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}


def validate_label_file(label_path: Path) -> dict:
    """Validate a single YOLO-Pose label file."""
    errors = []
    stats = {"visible": 0, "occluded": 0, "missing": 0, "total_kp": 0, "objects": 0}

    with open(label_path) as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split()
            if not parts:
                continue

            stats["objects"] += 1

            if len(parts) != EXPECTED_VALUES:
                errors.append(
                    f"Line {line_num}: expected {EXPECTED_VALUES} values, got {len(parts)}"
                )
                continue

            values = [float(v) for v in parts]

            # Check class ID
            class_id = int(values[0])
            if class_id != 0:
                errors.append(f"Line {line_num}: class ID should be 0, got {class_id}")

            # Check bbox normalization
            for i, name in zip(range(1, 5), ["x_center", "y_center", "width", "height"]):
                if not 0.0 <= values[i] <= 1.0:
                    errors.append(
                        f"Line {line_num}: {name}={values[i]:.4f} not in [0, 1]"
                    )

            # Check keypoints
            for kp_idx in range(NUM_KEYPOINTS):
                offset = 1 + BBOX_VALUES + (kp_idx * VALUES_PER_KP)
                kp_x, kp_y, vis = values[offset], values[offset + 1], values[offset + 2]

                vis_int = int(vis)
                if vis_int not in (0, 1, 2):
                    errors.append(
                        f"Line {line_num}: keypoint {kp_idx} ({KEYPOINT_NAMES[kp_idx]}) "
                        f"visibility={vis_int} not in {{0, 1, 2}}"
                    )

                stats["total_kp"] += 1
                if vis_int == 2:
                    stats["visible"] += 1
                elif vis_int == 1:
                    stats["occluded"] += 1
                else:
                    stats["missing"] += 1

                # Warn if occluded but coordinates are 0,0 (likely not annotated)
                if vis_int == 1 and kp_x == 0.0 and kp_y == 0.0:
                    if kp_idx in CRITICAL_NODES:
                        errors.append(
                            f"Line {line_num}: keypoint {kp_idx} ({KEYPOINT_NAMES[kp_idx]}) "
                            f"marked occluded but coords are (0,0) — must estimate position"
                        )

    return {"errors": errors, "stats": stats, "file": label_path.name}


def main():
    parser = argparse.ArgumentParser(
        description="Validate YOLO-Pose annotations for cricket bowling"
    )
    parser.add_argument(
        "--labels-dir",
        type=Path,
        required=True,
        help="Directory containing .txt label files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit)",
    )
    args = parser.parse_args()

    label_files = sorted(args.labels_dir.glob("*.txt"))
    if not label_files:
        print(f"No .txt files found in {args.labels_dir}")
        return

    total_errors = 0
    total_stats = {"visible": 0, "occluded": 0, "missing": 0, "total_kp": 0, "objects": 0}

    for label_file in label_files:
        result = validate_label_file(label_file)
        for key in total_stats:
            total_stats[key] += result["stats"][key]
        if result["errors"]:
            total_errors += len(result["errors"])
            print(f"\n{result['file']}:")
            for err in result["errors"]:
                print(f"  {err}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Files checked: {len(label_files)}")
    print(f"Total objects: {total_stats['objects']}")
    print(f"Total errors:  {total_errors}")
    if total_stats["total_kp"] > 0:
        t = total_stats["total_kp"]
        print(f"\nKeypoint visibility breakdown:")
        print(f"  Visible (2):  {total_stats['visible']:5d} ({100*total_stats['visible']/t:.1f}%)")
        print(f"  Occluded (1): {total_stats['occluded']:5d} ({100*total_stats['occluded']/t:.1f}%)")
        print(f"  Missing (0):  {total_stats['missing']:5d} ({100*total_stats['missing']/t:.1f}%)")

    if total_errors > 0 and args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
