from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # YouTube
    youtube_client_secrets_file: str = Field(default="client_secrets.json")
    youtube_token_file: str = Field(default="youtube_token.json")

    # Recording
    screen_resolution: str = Field(default="1920x1080")
    screen_fps: int = Field(default=30)
    webcam_device: str = Field(default="/dev/video0")
    audio_device: str = Field(default="default")

    # Paths
    output_dir: Path = Field(default=Path("output"))
    recordings_dir: Path = Field(default=Path("recordings"))
    max_video_duration_minutes: int = Field(default=60)

    # Claude
    claude_model: str = Field(default="claude-sonnet-4-6")

    # Channel / social links (appended to every video description)
    channel_twitter: str = Field(default="")
    channel_twitch: str = Field(default="")
    channel_instagram: str = Field(default="")
    channel_tiktok: str = Field(default="")
    channel_description_footer: str = Field(default="")

    def social_links_block(self) -> str:
        """Returns a formatted social links section for YouTube descriptions."""
        lines = []
        if self.channel_twitter:
            lines.append(f"🐦 Twitter: {self.channel_twitter}")
        if self.channel_twitch:
            lines.append(f"🎮 Twitch: {self.channel_twitch}")
        if self.channel_instagram:
            lines.append(f"📸 Instagram: {self.channel_instagram}")
        if self.channel_tiktok:
            lines.append(f"🎵 TikTok: {self.channel_tiktok}")
        if self.channel_description_footer:
            lines.append(self.channel_description_footer)
        if not lines:
            return ""
        return "\n\n---\n" + "\n".join(lines)

    @property
    def videos_dir(self) -> Path:
        return self.output_dir / "videos"

    @property
    def thumbnails_dir(self) -> Path:
        return self.output_dir / "thumbnails"

    @property
    def metadata_dir(self) -> Path:
        return self.output_dir / "metadata"

    @property
    def raw_recordings_dir(self) -> Path:
        return self.recordings_dir / "raw"

    @property
    def processed_recordings_dir(self) -> Path:
        return self.recordings_dir / "processed"

    def ensure_dirs(self) -> None:
        for d in [
            self.videos_dir,
            self.thumbnails_dir,
            self.metadata_dir,
            self.raw_recordings_dir,
            self.processed_recordings_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def screen_width(self) -> int:
        return int(self.screen_resolution.split("x")[0])

    @property
    def screen_height(self) -> int:
        return int(self.screen_resolution.split("x")[1])


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
