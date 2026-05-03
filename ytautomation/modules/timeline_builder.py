from __future__ import annotations

from pathlib import Path

import json

from ytautomation.core.errors import ValidationError
from ytautomation.core.io import write_model
from ytautomation.core.models import AudioManifest, JobSpec, TimelineArtifact, TimelineSegment
from ytautomation.core.settings import Settings


def _resolve_avatar(avatars_dir: Path, speaker: str, avatar_map: dict[str, str] | None) -> Path:
    if avatar_map and speaker in avatar_map:
        mapped = Path(avatar_map[speaker])
        candidate = mapped if mapped.is_absolute() else (avatars_dir / mapped)
        if candidate.exists():
            return candidate

    direct = avatars_dir / f"{speaker}.png"
    if direct.exists():
        return direct

    # Try any extension: speaker.*
    matches = sorted([p for p in avatars_dir.glob(f"{speaker}.*") if p.is_file()])
    if matches:
        return matches[0]

    raise ValidationError(
        f"Avatar not found for speaker '{speaker}'. Expected {direct} or any file named '{speaker}.*' in {avatars_dir}"
    )


def build_timeline(job: JobSpec, audio_manifest: AudioManifest, settings: Settings, output_dir: Path) -> TimelineArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = output_dir / "timeline.json"

    segments: list[TimelineSegment] = []
    cursor = 0.0

    avatar_map: dict[str, str] | None = None
    if settings.avatar_map_path and settings.avatar_map_path.exists():
        avatar_map = json.loads(settings.avatar_map_path.read_text(encoding="utf-8"))

    for clip in audio_manifest.clips:
        avatar = _resolve_avatar(settings.assets_avatars_dir, clip.speaker, avatar_map)
        segments.append(
            TimelineSegment(
                index=clip.index,
                speaker=clip.speaker,
                start_sec=cursor,
                duration_sec=clip.duration_sec,
                audio_path=clip.wav_path,
                avatar_path=avatar,
            )
        )
        cursor += clip.duration_sec

    artifact = TimelineArtifact(job_id=job.job_id, segments=segments, total_duration_sec=cursor)
    write_model(timeline_path, artifact)
    return artifact
