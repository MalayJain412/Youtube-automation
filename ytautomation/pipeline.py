from __future__ import annotations

import logging
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ytautomation.core.errors import ArtifactMissingError
from ytautomation.core.io import read_model, write_model
from ytautomation.core.logging import configure_logging
from ytautomation.core.models import AudioManifest, JobSpec, JobStatus, RenderPlan, ScriptArtifact, TimelineArtifact
from ytautomation.core.paths import ensure_dirs, safe_filename
from ytautomation.core.settings import Settings, get_settings
from ytautomation.modules.csv_ingest import load_jobs_from_csv
from ytautomation.modules.gameplay_selector import choose_gameplay_clip
from ytautomation.modules.llm_script_generator import generate_script
from ytautomation.modules.timeline_builder import build_timeline
from ytautomation.modules.tts_cartesia import generate_audio
from ytautomation.modules.video_renderer import render_video

logger = logging.getLogger(__name__)


_VALID_STEPS = {"script", "audio", "timeline", "render"}


def _normalize_steps(steps: list[str] | None) -> list[str]:
    if steps is None:
        return ["script", "audio", "timeline", "render"]

    normalized = [s.strip().lower() for s in steps if str(s).strip()]
    if not normalized:
        return ["script", "audio", "timeline", "render"]

    unknown = sorted(set(normalized) - _VALID_STEPS)
    if unknown:
        raise ValueError(f"Unknown steps: {unknown}. Valid steps: {sorted(_VALID_STEPS)}")

    # Keep original relative order while removing duplicates
    seen: set[str] = set()
    ordered: list[str] = []
    for s in normalized:
        if s not in seen:
            ordered.append(s)
            seen.add(s)
    return ordered


def _status_path(dirs: dict[str, Path]) -> Path:
    return dirs["input"].parent / "status.json"


def write_status(dirs: dict[str, Path], job_id: str, stage: str, ok: bool = True, message: str | None = None) -> None:
    write_model(_status_path(dirs), JobStatus(job_id=job_id, stage=stage, ok=ok, message=message))


def import_jobs(csv_path: Path, settings: Settings | None = None) -> list[JobSpec]:
    settings = settings or get_settings()
    jobs = load_jobs_from_csv(csv_path)

    for job in jobs:
        persist_job(job, settings=settings)

    return jobs


def persist_job(job: JobSpec, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    dirs = ensure_dirs(settings.runs_dir, job.job_id)
    path = dirs["input"] / "job.json"
    write_model(path, job)
    write_status(dirs, job.job_id, stage="imported")
    return path


def _load_audio_manifest(dirs: dict[str, Path]) -> AudioManifest:
    path = dirs["audio"] / "audio_manifest.json"
    if not path.exists():
        raise ArtifactMissingError("Missing audio_manifest.json. Run audio step first.")
    return read_model(path, AudioManifest)


def _load_timeline(dirs: dict[str, Path]) -> TimelineArtifact:
    path = dirs["timeline"] / "timeline.json"
    if not path.exists():
        raise ArtifactMissingError("Missing timeline.json. Run timeline step first.")
    return read_model(path, TimelineArtifact)


def _render_output_path(dirs: dict[str, Path], job: JobSpec) -> Path:
    return dirs["render"] / f"{safe_filename(job.topic, fallback=job.job_id)}.mp4"


def run_job(job_id: str, steps: list[str] | None = None, force: bool = False, settings: Settings | None = None) -> dict[str, str]:
    configure_logging()
    settings = settings or get_settings()

    dirs = ensure_dirs(settings.runs_dir, job_id)

    job_path = dirs["input"] / "job.json"
    if not job_path.exists():
        raise ArtifactMissingError(f"Missing job.json. Import first for job_id={job_id}")

    job = read_model(job_path, JobSpec)

    steps = _normalize_steps(steps)
    script: ScriptArtifact | None = None
    audio_manifest: AudioManifest | None = None
    timeline: TimelineArtifact | None = None

    try:
        if "script" in steps:
            write_status(dirs, job_id, stage="script")
            script = generate_script(job, settings, dirs["script"], force=force)

        if "audio" in steps:
            write_status(dirs, job_id, stage="audio")
            if script is None:
                script = generate_script(job, settings, dirs["script"], force=False)
            audio_manifest = generate_audio(job, script, settings, dirs["audio"], force=force)

        if "timeline" in steps:
            write_status(dirs, job_id, stage="timeline")
            timeline_path = dirs["timeline"] / "timeline.json"
            if timeline_path.exists() and not force:
                timeline = read_model(timeline_path, TimelineArtifact)
            else:
                if audio_manifest is None:
                    if script is None:
                        script = generate_script(job, settings, dirs["script"], force=False)
                    audio_manifest = generate_audio(job, script, settings, dirs["audio"], force=False)
                timeline = build_timeline(job, audio_manifest, settings, dirs["timeline"])

        if "render" in steps:
            write_status(dirs, job_id, stage="render")
            output_path = _render_output_path(dirs, job)
            render_plan_path = dirs["render"] / "render_plan.json"
            if output_path.exists() and render_plan_path.exists() and not force:
                read_model(render_plan_path, RenderPlan)
            else:
                if timeline is None:
                    timeline = _load_timeline(dirs)
                if script is None:
                    script = generate_script(job, settings, dirs["script"], force=False)
                gameplay_path, start_sec = choose_gameplay_clip(settings.assets_gameplay_dir, timeline.total_duration_sec)
                render_video(timeline, script, gameplay_path, start_sec, output_path, settings)

        # Sanity check: if a step was requested, its artifact should exist.
        if "script" in steps and not (dirs["script"] / "script.json").exists():
            raise ArtifactMissingError("Expected script.json to exist after script step")
        if "audio" in steps and not (dirs["audio"] / "audio_manifest.json").exists():
            raise ArtifactMissingError("Expected audio_manifest.json to exist after audio step")
        if "timeline" in steps and not (dirs["timeline"] / "timeline.json").exists():
            raise ArtifactMissingError("Expected timeline.json to exist after timeline step")
        if "render" in steps and not _render_output_path(dirs, job).exists():
            raise ArtifactMissingError(f"Expected {_render_output_path(dirs, job).name} to exist after render step")

        write_status(dirs, job_id, stage="done")
        return {
            "job": str(dirs["input"] / "job.json"),
            "script": str(dirs["script"] / "script.json"),
            "audio": str(dirs["audio"] / "audio_manifest.json"),
            "timeline": str(dirs["timeline"] / "timeline.json"),
            "video": str(_render_output_path(dirs, job)),
            "caption_metadata": str(_render_output_path(dirs, job).with_suffix(".caption.txt")),
        }

    except Exception as e:
        logger.exception("Job failed")
        write_status(dirs, job_id, stage="failed", ok=False, message=str(e))
        raise


if __name__ == "__main__":
    from ytautomation.cli import main

    main()
