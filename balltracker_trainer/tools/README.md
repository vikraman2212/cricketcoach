# Shared Video Download & Frame Extraction Tooling

Tooling shared between `ball-detector/` and `bowler-pose/` for acquiring and
preparing cricket bowling footage.

## Data Provenance Strategy

### Phase A — Prototyping (YouTube)

Use YouTube videos for rapid pipeline validation. **Dataset and model weights
stay PRIVATE.**

1. Curate URLs in `video_catalog.yaml` with metadata tags
2. Download with `download_videos.py`
3. Extract frames with `extract_frames.py`
4. Annotate and train — keep everything local and unpublished

### Phase B — Release (Clean Data)

Retrain on clean, permissively-licensed data so model weights can be **PUBLISHED**.

- **Own footage**: Record net sessions with phone/tripod behind the stumps
- **Permissive datasets**: Roboflow Universe, Kaggle (check licenses)
- **Synthetic data**: Augmented versions of own footage

Phase B entries in `video_catalog.yaml` should use `license: own_footage` or
`license: cc_by`.

## Workflow

```
1. Curate catalog    →  video_catalog.yaml
2. Download videos   →  python download_videos.py --ball-color red --angle behind_stumps
3. Extract frames    →  python extract_frames.py --video-dir raw_videos/ --output-dir ../ball-detector/datasets/cricket-ball --fps 30 --split
4. Annotate          →  CVAT / Roboflow (import extracted frames)
5. Train             →  cd ../ball-detector && python scripts/train.py
```

## Usage

### Download Videos

```bash
# Download all videos matching filters
python download_videos.py --ball-color red --angle behind_stumps

# Dry run (see what would be downloaded)
python download_videos.py --dry-run

# Download only own footage (Phase B)
python download_videos.py --license own_footage

# Custom output directory
python download_videos.py --output-dir /path/to/videos
```

### Extract Frames

```bash
# Ball detector: 30 FPS, PNG (lossless), with train/val split
python extract_frames.py \
    --video-dir raw_videos/ \
    --output-dir ../ball-detector/datasets/cricket-ball \
    --fps 30 --format png --split

# Bowler pose: 5 FPS, JPG (skeleton doesn't need lossless)
python extract_frames.py \
    --video-dir raw_videos/ \
    --output-dir ../bowler-pose/datasets/cricket-pose \
    --fps 5 --format jpg --split
```

## File Structure

```
tools/
├── README.md              # This file
├── requirements.txt       # yt-dlp, pyyaml, tqdm, opencv
├── video_catalog.yaml     # Curated video sources with metadata
├── download_videos.py     # YouTube downloader with catalog filtering
├── extract_frames.py      # Frame extractor with metadata sidecar JSONs
└── raw_videos/            # Downloaded videos (gitignored)
```

## Setup

```bash
pip install -r requirements.txt
```

yt-dlp also requires `ffmpeg` on the system path:

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg
```
