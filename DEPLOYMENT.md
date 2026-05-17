# Deployment Guide

This project is primarily a desktop downloader. To make it available for others, you have two practical paths.

## 1) Distribute as a desktop app (fastest path)

Use this if you want users to install and run locally.

### Build executable with PyInstaller

```bash
source env/bin/activate
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name TubeSwift download.py
```

Artifact is created in `dist/TubeSwift` (or `TubeSwift.exe` on Windows).

### Publish

1. Create a GitHub repository.
2. Upload the binary to a GitHub Release.
3. Add install notes per OS in release description.

## 2) Host as a web service (scalable path)

Use this if users should access via browser.

### Recommended architecture

1. Frontend: React/Next.js or simple Streamlit UI.
2. API: FastAPI service to accept jobs.
3. Worker: background queue (Celery/RQ) running `yt-dlp`.
4. Storage: S3-compatible bucket for downloaded files.
5. Database: Postgres for job status.
6. Deployment: Render/Fly.io/Railway/AWS.

### Flow

1. User submits video URL.
2. API validates input, creates job ID.
3. Worker downloads to temporary storage.
4. Worker uploads output to object storage.
5. API returns signed download URL.

### Why queue workers are necessary

Downloads are long-running and CPU/network heavy. Running directly in a request handler will time out and scale poorly.

## Security and policy checklist

- Rate limit incoming jobs per IP/user.
- Add abuse monitoring and file-size limits.
- Enforce allowed domains and URL validation.
- Keep temporary files on short retention.
- Review YouTube Terms of Service and local legal obligations before public hosting.

## Suggested roadmap

1. Ship desktop binary first (1-2 days).
2. Add hosted API prototype for private users.
3. Add auth + billing + quotas before public launch.
