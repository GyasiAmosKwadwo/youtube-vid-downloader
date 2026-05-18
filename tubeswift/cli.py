import argparse
import sys
from pathlib import Path

from .downloader import DownloadEngine
from .models import DownloadSettings, ProgressUpdate
from .preflight import PreflightError, ensure_ffmpeg, ensure_output_dir, validate_youtube_url


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TubeSwift CLI fallback downloader")
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument(
        "-o",
        "--output",
        default=str(Path.home() / "Downloads"),
        help="Output folder",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=1080,
        choices=[360, 480, 720, 1080],
        help="Maximum video height",
    )
    parser.add_argument(
        "--profile",
        default="Turbo",
        choices=["Balanced", "Turbo", "Extreme"],
        help="Throughput tuning profile",
    )
    parser.add_argument(
        "--output-mode",
        default="Fastest",
        choices=["Fastest", "MP4 Compatible"],
        help="Fastest skips forced remux when possible; MP4 Compatible prioritizes mp4 output",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        validate_youtube_url(args.url)
        output_dir = Path(args.output)
        ensure_output_dir(output_dir)
        ensure_ffmpeg()
    except PreflightError as exc:
        print(f"Preflight failed: {exc}")
        return 1

    settings = DownloadSettings(
        url=args.url,
        output_dir=output_dir,
        max_height=args.quality,
        performance_profile=args.profile,
        output_mode=args.output_mode,
    )

    def on_log(message: str) -> None:
        print(message)

    def on_progress(update: ProgressUpdate) -> None:
        print(f"{update.percent:5.1f}% | {update.status} | {update.meta}", end="\r", flush=True)

    engine = DownloadEngine(
        settings=settings,
        on_log=on_log,
        on_progress=on_progress,
        should_cancel=lambda: False,
    )

    try:
        engine.run()
        print("\nDone.")
        return 0
    except Exception as exc:
        print(f"\nDownload failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
