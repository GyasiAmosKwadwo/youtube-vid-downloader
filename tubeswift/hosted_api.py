import os
import queue
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .downloader import DownloadCancelled, DownloadEngine
from .ffmpeg import discover_ffmpeg
from .models import DownloadSettings, ProgressUpdate
from .preflight import PreflightError, ensure_ffmpeg, ensure_output_dir, validate_youtube_url


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CreateJobRequest(BaseModel):
    url: str
    max_height: int = Field(default=1080)
    performance_profile: str = Field(default="Turbo")
    output_mode: str = Field(default="Fastest")


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str


class JobStore:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._queue: queue.Queue[str] = queue.Queue()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def create_job(self, payload: CreateJobRequest) -> dict[str, Any]:
        try:
            validate_youtube_url(payload.url)
        except PreflightError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if payload.max_height not in {360, 480, 720, 1080}:
            raise HTTPException(status_code=422, detail="max_height must be one of 360, 480, 720, 1080")

        if payload.performance_profile not in {"Balanced", "Turbo", "Extreme"}:
            raise HTTPException(status_code=422, detail="Invalid performance_profile")

        if payload.output_mode not in {"Fastest", "MP4 Compatible"}:
            raise HTTPException(status_code=422, detail="Invalid output_mode")

        job_id = uuid.uuid4().hex
        job_dir = self.storage_root / job_id
        output_dir = job_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "job_id": job_id,
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "finished_at": None,
            "progress_percent": 0.0,
            "status_text": "Queued",
            "meta": "Speed: -- | Avg: -- | ETA: --",
            "request": payload.model_dump(),
            "output_dir": str(output_dir),
            "archive_path": None,
            "files": [],
            "error": None,
            "cancel_requested": False,
            "logs": [],
        }

        with self._lock:
            self._jobs[job_id] = record
            self._queue.put(job_id)

        return record.copy()

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._public_snapshot(j) for j in self._jobs.values()]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None
            return self._public_snapshot(record)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                raise HTTPException(status_code=404, detail="Job not found")

            if record["status"] in {"completed", "failed", "cancelled"}:
                return self._public_snapshot(record)

            record["cancel_requested"] = True
            record["status_text"] = "Cancellation requested"
            self._append_log(record, "Cancellation requested by API client.")
            return self._public_snapshot(record)

    def get_archive_path(self, job_id: str) -> Path:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                raise HTTPException(status_code=404, detail="Job not found")
            if record["status"] != "completed":
                raise HTTPException(status_code=409, detail="Job is not completed")
            archive = record.get("archive_path")
            if not archive:
                raise HTTPException(status_code=500, detail="Archive not available")
            return Path(archive)

    def _public_snapshot(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": record["job_id"],
            "status": record["status"],
            "created_at": record["created_at"],
            "started_at": record["started_at"],
            "finished_at": record["finished_at"],
            "progress_percent": record["progress_percent"],
            "status_text": record["status_text"],
            "meta": record["meta"],
            "request": record["request"],
            "files": list(record["files"]),
            "error": record["error"],
            "cancel_requested": record["cancel_requested"],
            "logs": list(record["logs"]),
        }

    @staticmethod
    def _append_log(record: dict[str, Any], message: str) -> None:
        timestamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        record["logs"].append(timestamped)
        if len(record["logs"]) > 250:
            record["logs"] = record["logs"][-250:]

    def _worker_loop(self) -> None:
        while True:
            job_id = self._queue.get()

            with self._lock:
                record = self._jobs.get(job_id)
                if not record:
                    self._queue.task_done()
                    continue
                if record["cancel_requested"]:
                    record["status"] = "cancelled"
                    record["finished_at"] = utc_now()
                    self._append_log(record, "Job cancelled before start.")
                    self._queue.task_done()
                    continue

                record["status"] = "running"
                record["status_text"] = "Starting..."
                record["started_at"] = utc_now()
                self._append_log(record, "Job started.")

            started_monotonic = time.time()

            try:
                ensure_ffmpeg()
                output_dir = Path(record["output_dir"])
                ensure_output_dir(output_dir)

                request_data = record["request"]
                settings = DownloadSettings(
                    url=request_data["url"],
                    output_dir=output_dir,
                    max_height=request_data["max_height"],
                    performance_profile=request_data["performance_profile"],
                    output_mode=request_data["output_mode"],
                )

                def on_log(msg: str) -> None:
                    with self._lock:
                        current = self._jobs.get(job_id)
                        if not current:
                            return
                        self._append_log(current, msg)

                def on_progress(update: ProgressUpdate) -> None:
                    with self._lock:
                        current = self._jobs.get(job_id)
                        if not current:
                            return
                        current["progress_percent"] = float(update.percent)
                        current["status_text"] = update.status
                        current["meta"] = update.meta

                engine = DownloadEngine(
                    settings=settings,
                    on_log=on_log,
                    on_progress=on_progress,
                    should_cancel=lambda: self._is_cancelled(job_id),
                )
                engine.run()

                files = sorted(p.name for p in output_dir.glob("*") if p.is_file())
                if not files:
                    raise RuntimeError("No downloadable files were produced.")

                archive_path = output_dir.parent / f"{job_id}.zip"
                with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for file_name in files:
                        file_path = output_dir / file_name
                        zf.write(file_path, arcname=file_name)

                with self._lock:
                    current = self._jobs.get(job_id)
                    if current:
                        current["status"] = "completed"
                        current["finished_at"] = utc_now()
                        current["progress_percent"] = 100.0
                        current["status_text"] = "Completed"
                        current["files"] = files
                        current["archive_path"] = str(archive_path)
                        elapsed = max(time.time() - started_monotonic, 0.1)
                        self._append_log(current, f"Completed in {elapsed:.1f}s")

            except DownloadCancelled:
                with self._lock:
                    current = self._jobs.get(job_id)
                    if current:
                        current["status"] = "cancelled"
                        current["finished_at"] = utc_now()
                        current["status_text"] = "Cancelled"
                        self._append_log(current, "Cancelled while downloading.")

            except Exception as exc:
                with self._lock:
                    current = self._jobs.get(job_id)
                    if current:
                        current["status"] = "failed"
                        current["finished_at"] = utc_now()
                        current["status_text"] = "Failed"
                        current["error"] = str(exc)
                        self._append_log(current, f"Error: {exc}")

            finally:
                self._queue.task_done()

    def _is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return True
            return bool(record.get("cancel_requested"))


def _default_storage_root() -> Path:
    configured = os.getenv("TUBESWIFT_STORAGE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / "Downloads").resolve()


def _cors_origins_from_env() -> list[str]:
    raw = os.getenv("TUBESWIFT_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="TubeSwift Hosted API", version="1.0.0")
store = JobStore(storage_root=_default_storage_root())
cors_origins = _cors_origins_from_env()

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "TubeSwift Hosted API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "worker_alive": store._worker.is_alive(),
        "storage_root": str(store.storage_root),
        "ffmpeg": discover_ffmpeg() or "not-found",
    }


@app.post("/jobs", response_model=JobResponse)
def create_job(payload: CreateJobRequest) -> JobResponse:
    record = store.create_job(payload)
    return JobResponse(job_id=record["job_id"], status=record["status"], created_at=record["created_at"])


@app.get("/jobs")
def list_jobs() -> dict[str, Any]:
    return {"jobs": store.list_jobs()}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    record = store.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return record


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    return store.cancel_job(job_id)


@app.get("/jobs/{job_id}/download")
def download_job_archive(job_id: str) -> FileResponse:
    archive_path = store.get_archive_path(job_id)
    return FileResponse(
        archive_path,
        filename=archive_path.name,
        media_type="application/zip",
    )
