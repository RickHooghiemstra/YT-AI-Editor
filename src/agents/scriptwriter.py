"""
Generates a full video production plan using Claude.
Returns structured editing instructions: segments, timing, commentary, music cues.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.agents.analyzer import AnalysisResult
from src.modules.transcriber import Transcript
from src.prompts.interview import SessionProfile
from src.prompts.templates import SCRIPTWRITER_SYSTEM, SCRIPTWRITER_PROMPT, METADATA_PROMPT, METADATA_SYSTEM
from src.utils.config import get_settings

console = Console()


@dataclass
class VideoSegment:
    name: str
    source_start: float
    source_end: float
    speed_multiplier: float = 1.0
    commentary: str = ""
    music_mood: str = "energetic"
    include_webcam: bool = True
    caption: str = ""

    @property
    def duration(self) -> float:
        return (self.source_end - self.source_start) / self.speed_multiplier


@dataclass
class VideoScript:
    title_options: list[str]
    hook_script: str
    segments: list[VideoSegment]
    outro_script: str
    estimated_duration_seconds: float


@dataclass
class VideoMetadata:
    titles: list[dict]
    description: str
    tags: list[str]
    category_id: str
    thumbnail_text: str
    thumbnail_subtext: str

    @property
    def best_title(self) -> str:
        return self.titles[0]["title"] if self.titles else "Gaming Video"

    def to_dict(self) -> dict:
        return {
            "titles": self.titles,
            "best_title": self.best_title,
            "description": self.description,
            "tags": self.tags,
            "category_id": self.category_id,
            "thumbnail_text": self.thumbnail_text,
            "thumbnail_subtext": self.thumbnail_subtext,
        }


def generate_script(
    profile: SessionProfile,
    analysis: AnalysisResult,
    transcript: Transcript,
) -> VideoScript:
    """Generate a structured video production plan."""
    settings = get_settings()

    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = SCRIPTWRITER_PROMPT.format(
        game_name=profile.game_name,
        channel_name=profile.channel_name,
        video_type=profile.video_type,
        tone=profile.tone,
        target_length_minutes=profile.target_length_minutes,
        audience=profile.audience,
        special_moments=profile.special_moments or "None specified",
        analysis_summary=analysis.to_summary_text(),
        transcript_excerpt=transcript.excerpt(2000),
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating video script...", total=None)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=SCRIPTWRITER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

    raw = response.content[0].text
    return _parse_script(raw)


def generate_metadata(
    profile: SessionProfile,
    script: VideoScript,
    analysis: AnalysisResult,
) -> VideoMetadata:
    """Generate YouTube title, description, tags, and thumbnail text."""
    settings = get_settings()

    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    key_moments = ", ".join(
        m.description for m in analysis.top_moments(5)
    )

    prompt = METADATA_PROMPT.format(
        game_name=profile.game_name,
        video_type=profile.video_type,
        channel_name=profile.channel_name,
        audience=profile.audience,
        tone=profile.tone,
        key_moments=key_moments,
        script_summary=script.hook_script[:500],
        current_date=date.today().isoformat(),
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating YouTube metadata...", total=None)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            system=METADATA_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

    raw = response.content[0].text
    return _parse_metadata(raw)


def _parse_script(raw: str) -> VideoScript:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])

        segments = [
            VideoSegment(
                name=s.get("name", f"Segment {i+1}"),
                source_start=float(s.get("source_start", 0)),
                source_end=float(s.get("source_end", 60)),
                speed_multiplier=float(s.get("speed_multiplier", 1.0)),
                commentary=s.get("commentary", ""),
                music_mood=s.get("music_mood", "energetic"),
                include_webcam=bool(s.get("include_webcam", True)),
                caption=s.get("caption", ""),
            )
            for i, s in enumerate(data.get("segments", []))
        ]

        return VideoScript(
            title_options=data.get("title_options", ["Gaming Video"]),
            hook_script=data.get("hook_script", ""),
            segments=segments,
            outro_script=data.get("outro_script", ""),
            estimated_duration_seconds=float(data.get("estimated_duration_seconds", 300)),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        console.print(f"[yellow]Script parse warning: {e} — using fallback[/yellow]")
        return VideoScript(
            title_options=["Gaming Highlights"],
            hook_script="Check out this gaming session!",
            segments=[VideoSegment(name="Main", source_start=0, source_end=300)],
            outro_script="Thanks for watching!",
            estimated_duration_seconds=300,
        )


def _parse_metadata(raw: str) -> VideoMetadata:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return VideoMetadata(
            titles=data.get("titles", [{"title": "Gaming Video", "style": "general"}]),
            description=data.get("description", "Gaming video."),
            tags=data.get("tags", []),
            category_id=data.get("category_id", "20"),
            thumbnail_text=data.get("thumbnail_text", "GAMING"),
            thumbnail_subtext=data.get("thumbnail_subtext", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return VideoMetadata(
            titles=[{"title": "Gaming Video", "style": "general"}],
            description="Gaming video.",
            tags=["gaming", "gameplay"],
            category_id="20",
            thumbnail_text="GAMING",
            thumbnail_subtext="",
        )
