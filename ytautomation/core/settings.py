from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-02-15-preview"

    # Cartesia
    cartesia_api_key: str | None = None
    cartesia_version: str = "2024-06-10"
    cartesia_model_id: str = "sonic-3"
    cartesia_language: str = "hi"
    cartesia_speed: float = 0.95
    cartesia_emotion: str = "neutral"

    # Common paths (default relative to repository root)
    repo_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    assets_gameplay_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "youtube-videos-download" / "videos")
    assets_avatars_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "avatars")
    avatar_map_path: Path | None = None
    runs_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "runs")
    prompt_template_path: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "ytautomation" / "prompts" / "script_prompt.txt")

    # Rendering
    output_width: int = 1080
    output_height: int = 1920
    fps: int = 24

    # Simple voice mapping (defaults for your current two voices)
    voice_id_aniket: str = "7dbf4710-0998-4b2c-bacb-9cb25cc68572"
    voice_id_malay: str = "85f9e4e0-8ae6-4c81-a88d-dbd80bbff29a"
    voice_id_shubham: str = "b1e904fd-eaf5-4bae-a7f9-d141b7f06987"

    def model_post_init(self, __context: Any) -> None:
        default_root = Path(__file__).resolve().parents[2]
        self.repo_root = _resolve_path(self.repo_root, default_root)

        self.assets_gameplay_dir = _resolve_path(self.assets_gameplay_dir, self.repo_root)
        self.assets_avatars_dir = _resolve_path(self.assets_avatars_dir, self.repo_root)
        self.runs_dir = _resolve_path(self.runs_dir, self.repo_root)
        self.prompt_template_path = _resolve_path(self.prompt_template_path, self.repo_root)

        if self.avatar_map_path is not None:
            self.avatar_map_path = _resolve_path(self.avatar_map_path, self.repo_root)


def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if env_path.exists():
        return Settings(_env_file=str(env_path), _env_file_encoding="utf-8")
    return Settings()


def _resolve_path(path: Path, base: Path) -> Path:
    return path if path.is_absolute() else base / path
