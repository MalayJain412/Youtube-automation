from __future__ import annotations

import logging
from pathlib import Path

import requests

from ytautomation.core.moviepy_compat import AudioFileClip

from ytautomation.core.errors import ConfigError, ValidationError
from ytautomation.core.io import write_model, write_text
from ytautomation.core.models import AudioClipArtifact, AudioManifest, JobSpec, ScriptArtifact
from ytautomation.core.settings import Settings

logger = logging.getLogger(__name__)


def _voice_id_for_speaker(speaker: str, settings: Settings, job: JobSpec) -> str:
    # Prefer per-job mapping (from CSV) if provided.
    if speaker == job.character_a and job.voice_id_a:
        return job.voice_id_a
    if speaker == job.character_b and job.voice_id_b:
        return job.voice_id_b

    # Fallback defaults (works out of the box for aniket/malay jobs).
    mapping = {
        job.character_a: settings.voice_id_aniket,
        job.character_b: settings.voice_id_malay,
    }
    voice_id = mapping.get(speaker)
    if not voice_id:
        raise ValidationError(f"No voice mapping for speaker: {speaker}")
    return voice_id


def generate_audio(job: JobSpec, script: ScriptArtifact, settings: Settings, output_dir: Path, force: bool = False) -> AudioManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "audio_manifest.json"

    if manifest_path.exists() and not force:
        return AudioManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    if not settings.cartesia_api_key:
        raise ConfigError("Missing CARTESIA_API_KEY")

    api_url = "https://api.cartesia.ai/tts/bytes"

    clips: list[AudioClipArtifact] = []

    for idx, line in enumerate(script.lines):
        speaker = line.speaker
        voice_id = _voice_id_for_speaker(speaker, settings, job)
        wav_path = output_dir / f"{idx:02d}_{speaker}.wav"

        if wav_path.exists() and not force:
            a = AudioFileClip(str(wav_path))
            duration = float(a.duration)
            a.close()
            clips.append(AudioClipArtifact(index=idx, speaker=speaker, wav_path=wav_path, duration_sec=duration))
            continue

        payload = {
            "model_id": settings.cartesia_model_id,
            "transcript": line.text,
            "voice": {"mode": "id", "id": voice_id},
            "output_format": {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100,
            },
            "language": settings.cartesia_language,
            "generation_config": {
                "volume": 1,
                "speed": settings.cartesia_speed,
                "emotion": settings.cartesia_emotion,
            },
        }

        headers = {
            "Cartesia-Version": settings.cartesia_version,
            "Authorization": f"Bearer {settings.cartesia_api_key}",
            "Content-Type": "application/json",
        }

        logger.info("TTS line=%s speaker=%s", idx, speaker)
        resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            err_path = output_dir / f"{idx:02d}_{speaker}.error.txt"
            write_text(err_path, f"{resp.status_code}\n{resp.text}")
            raise ValidationError(f"Cartesia TTS failed ({resp.status_code}) for line {idx}")

        wav_path.write_bytes(resp.content)

        a = AudioFileClip(str(wav_path))
        duration = float(a.duration)
        a.close()

        clips.append(AudioClipArtifact(index=idx, speaker=speaker, wav_path=wav_path, duration_sec=duration))

    manifest = AudioManifest(job_id=job.job_id, clips=clips)
    write_model(manifest_path, manifest)
    return manifest
