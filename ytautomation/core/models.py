from __future__ import annotations

from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    topic: str
    character_a: str
    character_b: str
    voice_id_a: str | None = None
    voice_id_b: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DialogueLine(BaseModel):
    speaker: str
    text: str


class ScriptArtifact(BaseModel):
    job_id: str
    prompt_used: str
    raw_response_text_path: Path
    parsed_script_path: Path
    caption_metadata: str
    lines: list[DialogueLine]


class AudioClipArtifact(BaseModel):
    index: int
    speaker: str
    wav_path: Path
    duration_sec: float


class AudioManifest(BaseModel):
    job_id: str
    clips: list[AudioClipArtifact]


class TimelineSegment(BaseModel):
    index: int
    speaker: str
    start_sec: float
    duration_sec: float
    audio_path: Path
    avatar_path: Path


class TimelineArtifact(BaseModel):
    job_id: str
    segments: list[TimelineSegment]
    total_duration_sec: float


class RenderPlan(BaseModel):
    job_id: str
    gameplay_path: Path
    gameplay_start_sec: float
    total_duration_sec: float
    output_path: Path
    caption_metadata_path: Path


class JobStatus(BaseModel):
    job_id: str
    stage: str
    ok: bool = True
    message: str | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
