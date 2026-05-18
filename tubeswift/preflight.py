from pathlib import Path
from urllib.parse import urlparse

from .ffmpeg import discover_ffmpeg


class PreflightError(ValueError):
    pass


def validate_youtube_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise PreflightError("URL must start with http:// or https://")

    host = (parsed.netloc or "").lower()
    valid_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }

    if host not in valid_hosts:
        raise PreflightError("Please provide a valid YouTube URL (youtube.com or youtu.be).")


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".tubeswift_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise PreflightError(f"Output folder is not writable: {path}") from exc
    finally:
        if probe.exists():
            probe.unlink(missing_ok=True)


def ensure_ffmpeg() -> None:
    if discover_ffmpeg() is None:
        raise PreflightError(
            "ffmpeg is unavailable. Install system ffmpeg or run: pip install imageio-ffmpeg"
        )
