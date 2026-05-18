from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DownloadSettings:
    url: str
    output_dir: Path
    max_height: int
    performance_profile: str
    output_mode: str


@dataclass(frozen=True)
class ProgressUpdate:
    percent: float
    status: str
    meta: str
