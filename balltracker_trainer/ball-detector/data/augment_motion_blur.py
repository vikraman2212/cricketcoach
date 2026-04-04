"""Synthetic motion blur augmentation for ball detection training.

Applies directional blur kernels to simulate ball speed (120-150+ km/h).
Generates multiple augmented copies per source image with varying blur
intensity and direction. Preserves original annotations (bbox unchanged
since blur is applied to the full frame).
"""

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# Blur intensities mapped to approximate ball speeds
BLUR_PRESETS = {
    "light": 7,       # ~80-100 km/h (medium pace)
    "medium": 15,     # ~120 km/h (fast-medium)
    "heavy": 25,      # ~140 km/h (fast)
    "extreme": 35,    # ~150+ km/h (express pace)
}


def apply_motion_blur(
    image: np.ndarray, kernel_size: int, angle_deg: float
) -> np.ndarray:
    """Apply directional motion blur at a given angle."""
    # Create motion blur kernel
    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    center = kernel_size // 2
    kernel[center, :] = 1.0
    kernel /= kernel_size

    # Rotate kernel to desired angle
    rotation_matrix = cv2.getRotationMatrix2D(
        (center, center), angle_deg, 1.0
    )
    kernel = cv2.warpAffine(
        kernel,
        rotation_matrix,
        (kernel_size, kernel_size),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    # Re-normalize after rotation
    kernel_sum = kernel.sum()
    if kernel_sum > 0:
        kernel /= kernel_sum

    return cv2.filter2D(image, -1, kernel)


def main():
    parser = argparse.ArgumentParser(
        description="Generate motion-blurred augmentations for ball detection"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing source images",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for augmented copies",
    )
    parser.add_argument(
        "--intensity",
        choices=list(BLUR_PRESETS.keys()),
        default="medium",
        help="Blur intensity preset (default: medium)",
    )
    parser.add_argument(
        "--copies",
        type=int,
        default=2,
        help="Number of augmented copies per image (default: 2)",
    )
    parser.add_argument(
        "--angle-range",
        type=float,
        nargs=2,
        default=[-15.0, 15.0],
        help="Trajectory angle range in degrees (default: -15 to +15)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed"
    )
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    kernel_size = BLUR_PRESETS[args.intensity]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    image_extensions = {".png", ".jpg", ".jpeg"}
    images = [
        f
        for f in sorted(args.input_dir.iterdir())
        if f.suffix.lower() in image_extensions
    ]

    if not images:
        print(f"No images found in {args.input_dir}")
        return

    total = len(images) * args.copies
    print(
        f"Generating {total} augmented images "
        f"({len(images)} sources × {args.copies} copies, "
        f"blur={args.intensity}/{kernel_size}px)"
    )

    for img_path in tqdm(images, desc="Augmenting"):
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"Warning: could not read {img_path}")
            continue

        for i in range(args.copies):
            angle = random.uniform(args.angle_range[0], args.angle_range[1])
            blurred = apply_motion_blur(image, kernel_size, angle)

            out_name = (
                f"{img_path.stem}_blur_{args.intensity}_{i:02d}{img_path.suffix}"
            )
            cv2.imwrite(str(args.output_dir / out_name), blurred)

    print(f"Done. Augmented images saved to {args.output_dir}")


if __name__ == "__main__":
    main()
