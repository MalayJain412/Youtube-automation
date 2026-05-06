from __future__ import annotations

import re
from pathlib import Path


def job_dir(runs_dir: Path, job_id: str) -> Path:
    return runs_dir / job_id


def stage_dir(runs_dir: Path, job_id: str, stage: str) -> Path:
    return job_dir(runs_dir, job_id) / stage


def ensure_dirs(runs_dir: Path, job_id: str) -> dict[str, Path]:
    dirs = {
        "input": stage_dir(runs_dir, job_id, "00_input"),
        "script": stage_dir(runs_dir, job_id, "01_script"),
        "audio": stage_dir(runs_dir, job_id, "02_audio"),
        "timeline": stage_dir(runs_dir, job_id, "03_timeline"),
        "render": stage_dir(runs_dir, job_id, "04_render"),
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


def safe_filename(value: str, fallback: str = "video", max_length: int = 80) -> str:
    normalized = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
    normalized = re.sub(r"\s+", "_", normalized.strip())
    normalized = normalized.strip("._")
    if not normalized:
        normalized = fallback
    return normalized[:max_length].rstrip("._") or fallback
