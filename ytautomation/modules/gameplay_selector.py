from __future__ import annotations

import random
from pathlib import Path

from ytautomation.core.moviepy_compat import VideoFileClip

from ytautomation.core.errors import ValidationError


def choose_gameplay_clip(gameplay_dir: Path, total_duration_sec: float, seed: int | None = None) -> tuple[Path, float]:
    if seed is not None:
        random.seed(seed)

    candidates = [p for p in gameplay_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv"}]
    if not candidates:
        raise ValidationError(f"No gameplay videos found in {gameplay_dir}")

    random.shuffle(candidates)

    for path in candidates:
        clip = VideoFileClip(str(path))
        try:
            if clip.duration is None:
                continue
            if clip.duration >= total_duration_sec + 0.25:
                max_start = float(clip.duration - total_duration_sec)
                start = random.uniform(0, max_start)
                return path, start
        finally:
            clip.close()

    raise ValidationError(
        f"No gameplay file long enough for required duration={total_duration_sec:.2f}s in {gameplay_dir}"
    )
