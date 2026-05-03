from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from ytautomation.core.logging import configure_logging
from ytautomation.core.models import JobSpec
from ytautomation.core.settings import Settings, get_settings
from ytautomation.orchestrator.csv_controller import CsvJobStore
from ytautomation.pipeline import persist_job, run_job

logger = logging.getLogger(__name__)

RunJobFn = Callable[[str], object]


class JobManager:
    def __init__(
        self,
        csv_path: Path,
        settings: Settings | None = None,
        max_retries: int = 3,
        run_job_func: RunJobFn | None = None,
    ):
        self.csv_path = csv_path
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.store = CsvJobStore(csv_path)
        self._run_job_func = run_job_func

    def run(self) -> dict[str, object]:
        configure_logging()
        self.store.save()

        pending = self.store.pending_jobs()
        results: list[dict[str, object]] = []

        for csv_job in pending:
            result = self._run_one(csv_job.index, csv_job.spec)
            results.append(result)

        return {
            "csv_path": str(self.csv_path),
            "pending_found": len(pending),
            "completed": len([r for r in results if r["status"] == "done"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results,
        }

    def _run_one(self, index: int, job: JobSpec) -> dict[str, object]:
        last_error = ""

        while self._retries(index) < self.max_retries:
            try:
                persist_job(job, settings=self.settings)
                self.store.set_status(index, "running", "")
                self.store.save()

                if self._run_job_func is None:
                    run_job(job.job_id, settings=self.settings)
                else:
                    self._run_job_func(job.job_id)

                self.store.set_status(index, "done", "")
                self.store.save()
                return {"job_id": job.job_id, "status": "done", "error": ""}
            except Exception as exc:
                last_error = str(exc)
                retries = self.store.increment_retries(index)
                logger.exception("Job failed: %s attempt=%s", job.job_id, retries)

                if retries >= self.max_retries:
                    self.store.set_status(index, "failed", last_error)
                    self.store.save()
                    return {"job_id": job.job_id, "status": "failed", "error": last_error}

                self.store.set_status(index, "pending", last_error)
                self.store.save()

        self.store.set_status(index, "failed", last_error or "Max retries exceeded")
        self.store.save()
        return {"job_id": job.job_id, "status": "failed", "error": last_error}

    def _retries(self, index: int) -> int:
        return int(self.store.df.loc[index, "retries"])

    def get_job(self, job_id: str) -> dict[str, object] | None:
        job = self.store.get(job_id)
        if job is None:
            return None

        return {
            "job_id": job.spec.job_id,
            "topic": job.spec.topic,
            "character_a": job.spec.character_a,
            "character_b": job.spec.character_b,
            "status": job.status,
            "error": job.error,
            "retries": job.retries,
        }


def run_all_jobs(csv_path: Path | str, settings: Settings | None = None, max_retries: int = 3) -> dict[str, object]:
    return JobManager(Path(csv_path), settings=settings, max_retries=max_retries).run()
