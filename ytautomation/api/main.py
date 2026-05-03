from __future__ import annotations

import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from ytautomation.core.io import read_json
from ytautomation.core.settings import get_settings
from ytautomation.orchestrator.job_manager import JobManager, run_all_jobs

DEFAULT_CSV_PATH = "data/input/topics.csv"

app = FastAPI(title="YouTube Automation Pipeline", version="0.2.0")


class RunRequest(BaseModel):
    csv_path: str = DEFAULT_CSV_PATH
    max_retries: int = 3


@app.get("/healthz")
def healthz() -> dict[str, object]:
    settings = get_settings()
    return {
        "ok": True,
        "cwd": os.getcwd(),
        "runs_dir": str(settings.runs_dir),
    }


@app.post("/run")
def run_pipeline(background: BackgroundTasks, req: RunRequest | None = None) -> dict[str, object]:
    request = req or RunRequest()
    csv_path = Path(request.csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=400, detail=f"CSV not found: {csv_path}")

    def _task() -> None:
        run_all_jobs(csv_path, max_retries=request.max_retries)

    background.add_task(_task)
    return {"status": "running", "csv_path": str(csv_path)}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, csv_path: str = DEFAULT_CSV_PATH) -> dict[str, object]:
    settings = get_settings()
    csv = Path(csv_path)

    csv_status = None
    if csv.exists():
        csv_status = JobManager(csv, settings=settings).get_job(job_id)

    job_root = settings.runs_dir / job_id
    status_path = job_root / "status.json"

    if csv_status is None and not job_root.exists():
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    artifacts = {
        "job": job_root / "00_input" / "job.json",
        "script_raw": job_root / "01_script" / "raw.txt",
        "script_json": job_root / "01_script" / "script.json",
        "audio_manifest": job_root / "02_audio" / "audio_manifest.json",
        "timeline": job_root / "03_timeline" / "timeline.json",
        "render_plan": job_root / "04_render" / "render_plan.json",
        "final_video": job_root / "04_render" / "final.mp4",
    }

    return {
        "job_id": job_id,
        "csv": csv_status,
        "pipeline": read_json(status_path) if status_path.exists() else None,
        "artifacts": {name: str(path) for name, path in artifacts.items()},
        "exists": {name: path.exists() for name, path in artifacts.items()},
    }
