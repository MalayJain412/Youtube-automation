from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ytautomation.core.models import JobSpec
from ytautomation.modules.csv_ingest import slugify

VALID_STATUSES = {"pending", "running", "done", "failed"}


@dataclass(frozen=True)
class CsvJob:
    index: int
    spec: JobSpec
    status: str
    retries: int
    error: str


class CsvJobStore:
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if "status" not in self.df.columns:
            if "done" in self.df.columns:
                self.df["status"] = self.df["done"].apply(lambda value: "done" if _is_truthy(value) else "pending")
            else:
                self.df["status"] = "pending"

        if "error" not in self.df.columns:
            self.df["error"] = ""

        if "retries" not in self.df.columns:
            self.df["retries"] = 0

        self.df["status"] = self.df["status"].apply(_normalize_status)
        self.df["error"] = self.df["error"].fillna("").astype(str)
        self.df["retries"] = self.df["retries"].fillna(0).apply(_to_int)

    def save(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.df.to_csv(self.csv_path, index=False)

    def pending_jobs(self) -> list[CsvJob]:
        jobs: list[CsvJob] = []
        for idx, row in self.df[self.df["status"] == "pending"].iterrows():
            jobs.append(self._job_from_row(int(idx), row))
        return jobs

    def recover_running(self) -> None:
        running = self.df["status"] == "running"
        self.df.loc[running, "status"] = "pending"

    def get(self, job_id: str) -> CsvJob | None:
        for idx, row in self.df.iterrows():
            spec = self._spec_from_row(int(idx), row)
            if spec.job_id == job_id:
                return CsvJob(
                    index=int(idx),
                    spec=spec,
                    status=str(row["status"]),
                    retries=_to_int(row["retries"]),
                    error="" if pd.isna(row["error"]) else str(row["error"]),
                )
        return None

    def set_status(self, index: int, status: str, error: str = "") -> None:
        normalized = _normalize_status(status)
        self.df.loc[index, "status"] = normalized
        self.df.loc[index, "error"] = error
        if "done" in self.df.columns:
            self.df.loc[index, "done"] = 1 if normalized == "done" else 0

    def increment_retries(self, index: int) -> int:
        retries = _to_int(self.df.loc[index, "retries"]) + 1
        self.df.loc[index, "retries"] = retries
        return retries

    def _job_from_row(self, index: int, row: pd.Series) -> CsvJob:
        return CsvJob(
            index=index,
            spec=self._spec_from_row(index, row),
            status=str(row["status"]),
            retries=_to_int(row["retries"]),
            error="" if pd.isna(row["error"]) else str(row["error"]),
        )

    def _spec_from_row(self, index: int, row: pd.Series) -> JobSpec:
        required = {"topic", "character_a", "character_b"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")

        topic = _clean(row["topic"])
        character_a = _clean(row["character_a"])
        character_b = _clean(row["character_b"])
        if not topic or not character_a or not character_b:
            raise ValueError(f"Empty fields at row {index}")

        raw_id = _clean(row["id"]) if "id" in self.df.columns else ""
        voice_id_a = _clean(row["voice_id_a"]) if "voice_id_a" in self.df.columns else None
        voice_id_b = _clean(row["voice_id_b"]) if "voice_id_b" in self.df.columns else None

        return JobSpec(
            job_id=raw_id or f"{slugify(topic)}-{index + 1}",
            topic=topic,
            character_a=character_a,
            character_b=character_b,
            voice_id_a=voice_id_a or None,
            voice_id_b=voice_id_b or None,
        )


def _clean(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def _to_int(value: Any) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _is_truthy(value: Any) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "done"}


def _normalize_status(status: Any) -> str:
    value = _clean(status).lower() or "pending"
    if value not in VALID_STATUSES:
        return "pending"
    return value
