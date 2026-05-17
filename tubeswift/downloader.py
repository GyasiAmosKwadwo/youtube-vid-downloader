import shutil
import time
from typing import Callable

import yt_dlp

from .ffmpeg import discover_ffmpeg
from .models import DownloadSettings, ProgressUpdate


class DownloadCancelled(Exception):
    pass


class DownloadEngine:
    PROFILE_CONFIG = {
        "Balanced": {
            "fragment_downloads": 8,
            "http_chunk_size": 8 * 1024 * 1024,
            "aria_connections": 16,
            "aria_split": 16,
            "aria_piece": "1M",
            "aria_min_split": "1M",
        },
        "Turbo": {
            "fragment_downloads": 16,
            "http_chunk_size": 16 * 1024 * 1024,
            "aria_connections": 24,
            "aria_split": 24,
            "aria_piece": "2M",
            "aria_min_split": "2M",
        },
        "Extreme": {
            "fragment_downloads": 24,
            "http_chunk_size": 32 * 1024 * 1024,
            "aria_connections": 32,
            "aria_split": 32,
            "aria_piece": "4M",
            "aria_min_split": "4M",
        },
    }

    def __init__(
        self,
        settings: DownloadSettings,
        on_log: Callable[[str], None],
        on_progress: Callable[[ProgressUpdate], None],
        should_cancel: Callable[[], bool],
    ) -> None:
        self.settings = settings
        self.on_log = on_log
        self.on_progress = on_progress
        self.should_cancel = should_cancel
        self._started_at: float | None = None

    @staticmethod
    def fmt_bytes_per_sec(speed: float | None) -> str:
        if not speed:
            return "--"
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        value = float(speed)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return "--"

    @staticmethod
    def fmt_eta(seconds: int | None) -> str:
        if seconds is None:
            return "--"
        try:
            seconds = int(seconds)
        except (ValueError, TypeError):
            return "--"
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {sec}s"
        if minutes > 0:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    def _progress_hook(self, data: dict) -> None:
        if self.should_cancel():
            raise DownloadCancelled("Download cancelled by user")

        status = data.get("status", "")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            percent = (downloaded / total * 100.0) if total else 0.0

            speed = self.fmt_bytes_per_sec(data.get("speed"))
            eta = self.fmt_eta(data.get("eta"))
            title = data.get("info_dict", {}).get("title", "Downloading...")

            avg_speed = "--"
            if self._started_at and downloaded:
                elapsed = max(time.time() - self._started_at, 0.1)
                avg_speed = self.fmt_bytes_per_sec(downloaded / elapsed)

            self.on_progress(
                ProgressUpdate(
                    percent=percent,
                    status=f"Downloading: {title}",
                    meta=f"Speed: {speed} | Avg: {avg_speed} | ETA: {eta}",
                )
            )

        elif status == "finished":
            self.on_log("Download finished. Finalizing media file...")
            self.on_progress(
                ProgressUpdate(
                    percent=100.0,
                    status="Finalizing...",
                    meta="Speed: -- | Avg: -- | ETA: 0s",
                )
            )

    def _build_format_selector(self) -> str:
        height = self.settings.max_height
        # Fastest prefers already muxed streams to avoid merge/remux overhead.
        if self.settings.output_mode == "Fastest":
            return f"b[height<={height}][vcodec!=none][acodec!=none]/bv*[height<={height}]+ba/best"

        # MP4 Compatible keeps compatibility-first behavior.
        return f"bv*[height<={height}]+ba/b[height<={height}]/best"

    def _build_options(self) -> dict:
        aria2_available = shutil.which("aria2c") is not None
        profile = self.PROFILE_CONFIG.get(self.settings.performance_profile, self.PROFILE_CONFIG["Balanced"])

        opts = {
            "outtmpl": str(self.settings.output_dir / "%(title)s.%(ext)s"),
            "format": self._build_format_selector(),
            "noplaylist": False,
            "continuedl": True,
            "overwrites": False,
            "retries": 6,
            "fragment_retries": 6,
            "extractor_retries": 3,
            "file_access_retries": 3,
            "concurrent_fragment_downloads": profile["fragment_downloads"],
            "buffersize": 4 * 1024 * 1024,
            "http_chunk_size": profile["http_chunk_size"],
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if self.settings.output_mode == "MP4 Compatible":
            opts["merge_output_format"] = "mp4"
            opts["remux_video"] = "mp4"

        ffmpeg_path = discover_ffmpeg()
        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path

        if aria2_available:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = [
                "-x",
                str(profile["aria_connections"]),
                "-s",
                str(profile["aria_split"]),
                "-k",
                str(profile["aria_piece"]),
                "--min-split-size",
                str(profile["aria_min_split"]),
                "--file-allocation=none",
                "--summary-interval=1",
            ]
            self.on_log(
                "aria2c enabled: high parallel connections for maximum throughput "
                f"({self.settings.performance_profile} profile)."
            )
        else:
            self.on_log("aria2c not found; using optimized native fragment downloader.")

        self.on_log(
            f"Profile={self.settings.performance_profile}, Output Mode={self.settings.output_mode}, "
            f"Fragments={profile['fragment_downloads']}, Chunk={profile['http_chunk_size'] // (1024 * 1024)}MB"
        )

        return opts

    def run(self) -> None:
        self._started_at = time.time()
        try:
            opts = self._build_options()
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.settings.url])
            duration = max(time.time() - self._started_at, 0.1)
            self.on_log(f"All downloads completed successfully in {duration:.1f}s.")
        except DownloadCancelled:
            raise
        except Exception as exc:
            if self.should_cancel():
                raise DownloadCancelled("Download cancelled by user") from exc
            raise RuntimeError(str(exc)) from exc
