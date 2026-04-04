"""Validate YOLO detection annotation files for cricket ball dataset.

Checks:
- Each label has exactly 5 values per line (class x_center y_center width height)
- Class ID is 0 (cricket_ball)
- Bounding box values are normalized [0, 1]
- Flags suspiciously large bboxes (likely false annotations — ball is small)
"""

import argparse
from pathlib import Path

EXPECTED_VALUES = 5  # class x_center y_center width height
MAX_BALL_BBOX_RATIO = 0.05  # Ball bbox shouldn't exceed 5% of image dimension


def validate_label_file(label_path: Path) -> dict:
    """Validate a single YOLO detection label file."""
    errors = []
    warnings = []
    stats = {"objects": 0, "suspicious_size": 0}

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

            # Check bbox size — ball should be very small in the frame
            w, h = values[3], values[4]
            if w > MAX_BALL_BBOX_RATIO or h > MAX_BALL_BBOX_RATIO:
                stats["suspicious_size"] += 1
                warnings.append(
                    f"Line {line_num}: bbox size ({w:.4f} x {h:.4f}) exceeds "
                    f"{MAX_BALL_BBOX_RATIO} — verify this is actually a ball"
                )

    return {
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "file": label_path.name,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate YOLO detection annotations for cricket ball"
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
    total_warnings = 0
    total_stats = {"objects": 0, "suspicious_size": 0}

    for label_file in label_files:
        result = validate_label_file(label_file)
        for key in total_stats:
            total_stats[key] += result["stats"][key]
        if result["errors"]:
            total_errors += len(result["errors"])
            print(f"\n{result['file']} [ERRORS]:")
            for err in result["errors"]:
                print(f"  {err}")
        if result["warnings"]:
            total_warnings += len(result["warnings"])
            print(f"\n{result['file']} [WARNINGS]:")
            for w in result["warnings"]:
                print(f"  {w}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Files checked:      {len(label_files)}")
    print(f"Total objects:      {total_stats['objects']}")
    print(f"Total errors:       {total_errors}")
    print(f"Total warnings:     {total_warnings}")
    print(f"Suspicious sizes:   {total_stats['suspicious_size']}")

    if total_errors > 0 or (args.strict and total_warnings > 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
