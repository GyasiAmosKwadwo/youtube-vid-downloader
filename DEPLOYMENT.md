# Deployment Guide

This repo now supports two production paths:

1. Desktop distribution with PyInstaller
2. Hosted API service with background worker and filesystem storage (no database)

## 1) Desktop release pipeline (fastest to ship)

### Local build

```bash
cd /Users/mac/Documents/projects/youtube-vid-downloader
source env/bin/activate
./scripts/build_desktop.sh
```

Build output:

- macOS/Linux: `dist/TubeSwift`
- Windows: `dist/TubeSwift.exe`

### Automated GitHub Releases

Workflow file: `.github/workflows/release-desktop.yml`

How it works:

1. Push a tag such as `v1.0.0`.
2. GitHub Actions builds binaries for macOS, Windows, Linux.
3. Artifacts are attached to the GitHub release.

Tag and push:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 2) Hosted product (no DB)

### Architecture

- FastAPI app for job APIs
- In-process background worker queue
- In-memory job state
- Filesystem storage for outputs and zip archives

No database is used.

Important tradeoff:

- Job metadata is lost when the service restarts.
- Downloaded files remain on disk.

### API entrypoint

- `tubeswift.hosted_api:app`

### Run locally

```bash
cd /Users/mac/Documents/projects/youtube-vid-downloader
source env/bin/activate
pip install -r requirements-hosted.txt
uvicorn tubeswift.hosted_api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
```

Storage root defaults to:

- `~/Downloads`

Override storage location:

```bash
export TUBESWIFT_STORAGE_ROOT=/absolute/path/to/storage
```

Optional CORS allow-list for browser clients:

```bash
export TUBESWIFT_CORS_ORIGINS=https://your-ui.example.com,https://admin.example.com
```

### Docker deployment

```bash
docker build -f Dockerfile.hosted -t tubeswift-hosted:latest .
docker run --rm -p 8000:8000 \
  -e TUBESWIFT_STORAGE_ROOT=/data/downloads \
  -v /absolute/host/path:/data/downloads \
  tubeswift-hosted:latest
```

### PaaS deployment (Procfile)

This repo includes a `Procfile` with:

- `web: uvicorn tubeswift.hosted_api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`

Use that command as-is on platforms like Railway/Render/Heroku-style runtimes.

### Render deployment (recommended for you)

This repo now includes `render.yaml` for Blueprint deploys.

What it configures:

- Python web service
- Build: `pip install -r requirements-hosted.txt`
- Start: `uvicorn tubeswift.hosted_api:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Persistent disk mounted at `/var/data` (storage root set to `/var/data/downloads`)

Steps:

1. Push this repo to GitHub.
2. In Render, click New + -> Blueprint.
3. Select your repository and apply the Blueprint.
4. In Render service Environment, set:
   - `TUBESWIFT_CORS_ORIGINS` to your frontend URL(s) (comma-separated).
5. Deploy and wait for the service to become live.

Verify:

```bash
curl https://YOUR-SERVICE.onrender.com/health
```

### Minimal API surface

- `GET /health`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /jobs/{job_id}/download`

### Example request

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "max_height": 1080,
    "performance_profile": "Turbo",
    "output_mode": "Fastest"
  }'
```

## Operational notes

- Install `aria2c` in the container/host for maximum speed.
- Apply reverse proxy limits and rate limiting before public exposure.
- Review legal/compliance obligations for public media downloading services.
- Keep `--workers 1` unless you add shared queue/state infrastructure (Redis + DB).
