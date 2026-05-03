from __future__ import annotations

import json
import logging
from pathlib import Path

from openai import AzureOpenAI

from ytautomation.core.errors import ConfigError, ValidationError
from ytautomation.core.io import write_json, write_text
from ytautomation.core.models import DialogueLine, JobSpec, ScriptArtifact
from ytautomation.core.settings import Settings

logger = logging.getLogger(__name__)


def _extract_json_array(text: str) -> str:
    """Best-effort extraction of a top-level JSON array from a model response."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValidationError("LLM output did not contain a JSON array")
    return text[start : end + 1]


def _validate_lines(lines: list[DialogueLine], job: JobSpec) -> None:
    allowed = {job.character_a, job.character_b}
    for i, line in enumerate(lines):
        if line.speaker not in allowed:
            raise ValidationError(f"Invalid speaker at line {i}: {line.speaker}")
        if not line.text.strip():
            raise ValidationError(f"Empty text at line {i}")

    # Strict alternation starting with character_a
    expected = job.character_a
    for i, line in enumerate(lines):
        if line.speaker != expected:
            raise ValidationError(
                f"Speakers must alternate starting with {job.character_a}; line {i} was {line.speaker}"
            )
        expected = job.character_b if expected == job.character_a else job.character_a


def generate_script(job: JobSpec, settings: Settings, output_dir: Path, force: bool = False) -> ScriptArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw.txt"
    parsed_path = output_dir / "script.json"

    if parsed_path.exists() and raw_path.exists() and not force:
        # Load existing parsed script
        data = json.loads(parsed_path.read_text(encoding="utf-8"))
        lines = [DialogueLine.model_validate(x) for x in data]
        _validate_lines(lines, job)
        return ScriptArtifact(
            job_id=job.job_id,
            prompt_used="(cached)",
            raw_response_text_path=raw_path,
            parsed_script_path=parsed_path,
            lines=lines,
        )

    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key or not settings.azure_openai_deployment:
        raise ConfigError("Azure OpenAI env vars missing: AZURE_OPENAI_ENDPOINT/API_KEY/DEPLOYMENT")

    prompt_template = settings.prompt_template_path.read_text(encoding="utf-8")
    prompt = prompt_template.format(
        topic=job.topic,
        character_a=job.character_a,
        character_b=job.character_b,
    )

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    logger.info("Generating script for job_id=%s", job.job_id)
    resp = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    text = (resp.choices[0].message.content or "").strip()
    write_text(raw_path, text)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = json.loads(_extract_json_array(text))

    if not isinstance(payload, list):
        raise ValidationError("LLM output JSON must be a list")

    lines = [DialogueLine.model_validate(x) for x in payload]
    _validate_lines(lines, job)

    write_json(parsed_path, [l.model_dump() for l in lines])

    return ScriptArtifact(
        job_id=job.job_id,
        prompt_used=prompt,
        raw_response_text_path=raw_path,
        parsed_script_path=parsed_path,
        lines=lines,
    )
