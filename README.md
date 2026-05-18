# TubeSwift Downloader

TubeSwift is a modern YouTube downloader with a futuristic desktop UI and an adaptive download engine powered by `yt-dlp`.

## What is new

- Futuristic, two-panel desktop UI with live telemetry and transfer log
- Adaptive throughput profiles:
  - `Balanced`
  - `Turbo`
  - `Extreme`
- Output strategy control:
  - `Fastest` (prefer muxed streams, less post-processing)
  - `MP4 Compatible` (compatibility-focused remux to mp4)
- Better runtime telemetry (instant speed + average speed + ETA)
- Preflight checks before download starts (URL, writable output, ffmpeg)
- Cancel support for active downloads
- CLI fallback if Tkinter is unavailable

## Important performance note

A guaranteed fixed speed boost (for example exactly 78%) is not technically possible across all videos and networks.
Speed depends on source throttling, network path, CDN region, and chosen output mode.

To maximize practical speed gains:

- Use `Turbo` or `Extreme`
- Use `Fastest` output mode
- Install `aria2c` for segmented acceleration
- Use wired or stable high-bandwidth internet

## Requirements

- Python 3.10+
- Tkinter support in your Python build (`_tkinter`) for GUI mode
- `ffmpeg` available either:
  - system-wide, or
  - from virtualenv package `imageio-ffmpeg`
- Optional: `aria2c` on PATH for faster segmented downloads

## Install

```bash
cd /Users/mac/Documents/projects/youtube-vid-downloader
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run

### GUI mode

```bash
python download.py
```

### CLI mode

```bash
python -m tubeswift.cli "https://www.youtube.com/watch?v=VIDEO_ID" \
  --profile Extreme \
  --output-mode Fastest \
  -q 1080
```

## Tkinter fix (if GUI is missing)

- macOS (Homebrew Python 3.11):
```bash
brew install python-tk@3.11
```

- Ubuntu/Debian:
```bash
sudo apt install python3-tk
```

## Optional accelerators

- macOS:
```bash
brew install aria2
```

- Ubuntu/Debian:
```bash
sudo apt install aria2
```

## Hosting and publishing

See [DEPLOYMENT.md](/Users/mac/Documents/projects/youtube-vid-downloader/DEPLOYMENT.md) for:

- Desktop app distribution (PyInstaller + GitHub Releases)
- Hosted web service architecture (API + queue + object storage)

## Project layout

- `download.py`: entrypoint (GUI with CLI fallback)
- `tubeswift/app.py`: GUI
- `tubeswift/downloader.py`: download engine and speed profiles
- `tubeswift/cli.py`: CLI mode
- `tubeswift/preflight.py`: input/dependency checks
- `tubeswift/models.py`: settings/progress models
- `tubeswift/ffmpeg.py`: ffmpeg discovery
