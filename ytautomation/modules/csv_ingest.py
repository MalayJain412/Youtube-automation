from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ytautomation.core.models import JobSpec


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "topic"


def load_jobs_from_csv(csv_path: Path) -> list[JobSpec]:
    df = pd.read_csv(csv_path)

    required = {"topic", "character_a", "character_b"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    jobs: list[JobSpec] = []
    for idx, row in df.iterrows():
        topic = str(row["topic"]).strip()
        a = str(row["character_a"]).strip()
        b = str(row["character_b"]).strip()
        if not topic or not a or not b:
            raise ValueError(f"Empty fields at row {idx}")

        raw_id = None
        if "id" in df.columns and str(row["id"]).strip() not in {"", "nan", "None"}:
            raw_id = str(row["id"]).strip()

        job_id = raw_id or f"{slugify(topic)}-{idx+1}"
        voice_id_a = None
        voice_id_b = None
        if "voice_id_a" in df.columns:
            voice_id_a = str(row["voice_id_a"]).strip()
            if voice_id_a.lower() in {"", "nan", "none"}:
                voice_id_a = None
        if "voice_id_b" in df.columns:
            voice_id_b = str(row["voice_id_b"]).strip()
            if voice_id_b.lower() in {"", "nan", "none"}:
                voice_id_b = None

        jobs.append(
            JobSpec(
                job_id=job_id,
                topic=topic,
                character_a=a,
                character_b=b,
                voice_id_a=voice_id_a,
                voice_id_b=voice_id_b,
            )
        )

    return jobs
