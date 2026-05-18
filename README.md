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
- Hosted API mode with queue worker and filesystem storage (no DB)

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

## Install (desktop/CLI)

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

Default output path is the OS Downloads folder (`~/Downloads`) unless you pass `--output`.

## Hosted API mode (no DB)

```bash
source env/bin/activate
pip install -r requirements-hosted.txt
uvicorn tubeswift.hosted_api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
```

Default hosted storage root is `~/Downloads`.
Override with `TUBESWIFT_STORAGE_ROOT=/absolute/path`.
Optional CORS list for a hosted frontend:
`TUBESWIFT_CORS_ORIGINS=https://your-ui.example.com,https://admin.example.com`

If hosted YouTube downloads fail with `Sign in to confirm you're not a bot`, set:
- `TUBESWIFT_YTDLP_COOKIE_FILE` (server-side cookies.txt path), or
- `TUBESWIFT_YTDLP_COOKIES_B64` (base64 cookies file contents)
- Optional: `TUBESWIFT_YT_PLAYER_CLIENTS`, `TUBESWIFT_YT_PO_TOKEN`, `TUBESWIFT_YT_VISITOR_DATA`

Automated PO token path (GetPOT provider plugins):
- `TUBESWIFT_YTDLP_ENABLE_GETPOT=true`
- `TUBESWIFT_YTDLP_GETPOT_PROVIDER_KEY=youtubepot-bgutilhttp`
- Optional: `TUBESWIFT_YTDLP_GETPOT_BASE_URL=http://127.0.0.1:4416`

## Desktop build and release

### Build locally with PyInstaller

```bash
source env/bin/activate
./scripts/build_desktop.sh
```

### Automated GitHub release builds

Push a tag like `v1.0.0`; workflow `.github/workflows/release-desktop.yml` builds and publishes binaries for macOS, Windows, and Linux.

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

## Deployment details

See [DEPLOYMENT.md](DEPLOYMENT.md) for production instructions.
For Render specifically, use the included `render.yaml` Blueprint file.

## Project layout

- `download.py`: entrypoint (GUI with CLI fallback)
- `tubeswift/app.py`: GUI
- `tubeswift/downloader.py`: download engine and speed profiles
- `tubeswift/cli.py`: CLI mode
- `tubeswift/hosted_api.py`: hosted API + in-process worker queue
- `tubeswift/preflight.py`: input/dependency checks
- `tubeswift/models.py`: settings/progress models
- `tubeswift/ffmpeg.py`: ffmpeg discovery
- `scripts/build_desktop.sh`: desktop packaging script
- `Dockerfile.hosted`: hosted image build
