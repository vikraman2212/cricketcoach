"""Download cricket bowling videos from the curated catalog.

Uses yt-dlp to fetch behind-the-stumps footage at best available quality.
Supports filtering by ball color, camera angle, bowling style, and laterality.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml


def load_catalog(catalog_path: Path) -> list[dict]:
    with open(catalog_path) as f:
        data = yaml.safe_load(f)
    return data.get("videos", [])


def filter_videos(
    videos: list[dict],
    ball_color: str | None = None,
    angle: str | None = None,
    bowling_style: str | None = None,
    laterality: str | None = None,
    license_filter: str | None = None,
) -> list[dict]:
    """Filter catalog entries by metadata fields."""
    filtered = videos
    if ball_color:
        filtered = [v for v in filtered if v.get("ball_color") == ball_color]
    if angle:
        filtered = [v for v in filtered if v.get("camera_angle") == angle]
    if bowling_style:
        filtered = [v for v in filtered if v.get("bowling_style") == bowling_style]
    if laterality:
        filtered = [v for v in filtered if v.get("laterality") == laterality]
    if license_filter:
        filtered = [v for v in filtered if v.get("license") == license_filter]
    return filtered


def download_video(
    url: str,
    output_dir: Path,
    dry_run: bool = False,
    cookies_from_browser: str | None = None,
) -> bool:
    """Download a single video using yt-dlp."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "yt_dlp",
        url,
        "-o", str(output_dir / "%(title)s_%(id)s.%(ext)s"),
        "-f", "bestvideo[height>=1080]+bestaudio/best[height>=1080]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--restrict-filenames",
        # JS runtime for YouTube n-challenge solving (requires node in PATH)
        "--js-runtimes", "node",
        # Download the EJS challenge solver from GitHub on first run
        "--remote-components", "ejs:github",
        # Write metadata JSON alongside the video — useful for dataset auditing
        "--write-info-json",
        # Skip unavailable videos instead of aborting the whole batch
        "--ignore-errors",
    ]

    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]

    if dry_run:
        print(f"  [DRY RUN] Would download: {url}")
        print(f"  Command: {' '.join(cmd)}")
        return True

    print(f"  Downloading: {url}")
    # Ensure Node.js is on PATH for the yt-dlp JS runtime (nvm installs to ~/.nvm)
    env = os.environ.copy()
    nvm_node = Path.home() / ".nvm" / "versions" / "node"
    if nvm_node.exists():
        latest = sorted(nvm_node.iterdir())[-1]
        env["PATH"] = str(latest / "bin") + os.pathsep + env.get("PATH", "")

    # Stream yt-dlp output directly so progress bars are visible
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"  ERROR: yt-dlp exited with code {result.returncode}")
        return False

    print(f"  Done: {url}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download cricket bowling videos from catalog"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).parent / "video_catalog.yaml",
        help="Path to video catalog YAML",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "raw_videos",
        help="Directory to save downloaded videos",
    )
    parser.add_argument("--ball-color", choices=["red", "white", "pink"])
    parser.add_argument(
        "--angle", choices=["behind_stumps", "umpire_pov", "side_on"]
    )
    parser.add_argument(
        "--bowling-style", choices=["fast", "medium", "spin"]
    )
    parser.add_argument("--laterality", choices=["right", "left"])
    parser.add_argument(
        "--license", dest="license_filter", choices=["youtube", "cc_by", "own_footage"]
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between downloads (rate limiting)",
    )
    parser.add_argument(
        "--browser",
        default="safari",
        metavar="BROWSER",
        help="Browser to read cookies from for YouTube auth (default: safari). "
             "Options: safari, chrome, firefox, chromium. Pass 'none' to skip.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be downloaded without actually downloading",
    )
    args = parser.parse_args()

    cookies_browser = None if args.browser.lower() == "none" else args.browser

    videos = load_catalog(args.catalog)
    filtered = filter_videos(
        videos,
        ball_color=args.ball_color,
        angle=args.angle,
        bowling_style=args.bowling_style,
        laterality=args.laterality,
        license_filter=args.license_filter,
    )

    print(f"Catalog: {len(videos)} total, {len(filtered)} matched filters")

    if not filtered:
        print("No videos matched the specified filters.")
        return

    success = 0
    for i, entry in enumerate(filtered):
        url = entry["url"]
        bowler = entry.get("bowler_name", "unknown")
        print(f"\n[{i + 1}/{len(filtered)}] {bowler} ({entry.get('bowling_style', '?')})")

        if download_video(url, args.output_dir, dry_run=args.dry_run, cookies_from_browser=cookies_browser):
            success += 1

        if i < len(filtered) - 1 and not args.dry_run:
            time.sleep(args.delay)

    print(f"\nComplete: {success}/{len(filtered)} videos downloaded")


if __name__ == "__main__":
    main()
