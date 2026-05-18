import shutil
from typing import Optional


def discover_ffmpeg() -> Optional[str]:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg
    except Exception:
        return None

    try:
        local_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

    return local_ffmpeg or None
