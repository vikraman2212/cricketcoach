"""Ball-color-aware preprocessing for training data augmentation.

Applies HSV channel adjustments tailored to each ball color:
  - Red:   Boost saturation for better visibility against green pitch
  - White: CLAHE contrast enhancement to distinguish from white pads/clothing
  - Pink:  Enhance magenta channel for day-night visibility

Creates augmented copies alongside originals — does not replace source images.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm


def preprocess_red(image: np.ndarray) -> np.ndarray:
    """Boost saturation to make red ball more prominent."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    # Boost saturation by 30% (capped at 255)
    s = np.clip(s.astype(np.float32) * 1.3, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)


def preprocess_white(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE contrast enhancement for white ball visibility."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    return cv2.cvtColor(cv2.merge([l_channel, a, b]), cv2.COLOR_LAB2BGR)


def preprocess_pink(image: np.ndarray) -> np.ndarray:
    """Enhance magenta/pink channel for day-night ball visibility."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    # Boost saturation in the pink/magenta hue range (140-170 in OpenCV)
    pink_mask = ((h >= 140) & (h <= 170)).astype(np.uint8)
    s = np.where(
        pink_mask, np.clip(s.astype(np.float32) * 1.4, 0, 255), s
    ).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)


PREPROCESSORS = {
    "red": preprocess_red,
    "white": preprocess_white,
    "pink": preprocess_pink,
}


def main():
    parser = argparse.ArgumentParser(
        description="Apply ball-color-aware preprocessing to training images"
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
        help="Directory for preprocessed copies",
    )
    parser.add_argument(
        "--ball-color",
        choices=["red", "white", "pink"],
        required=True,
        help="Ball color determines preprocessing strategy",
    )
    args = parser.parse_args()

    preprocess_fn = PREPROCESSORS[args.ball_color]
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

    print(f"Preprocessing {len(images)} images for {args.ball_color} ball")

    for img_path in tqdm(images, desc=f"Preprocessing ({args.ball_color})"):
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"Warning: could not read {img_path}")
            continue

        processed = preprocess_fn(image)
        out_path = args.output_dir / f"{img_path.stem}_color_{args.ball_color}{img_path.suffix}"
        cv2.imwrite(str(out_path), processed)

    print(f"Done. Preprocessed images saved to {args.output_dir}")


if __name__ == "__main__":
    main()
