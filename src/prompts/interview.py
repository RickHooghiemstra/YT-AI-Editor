"""Interactive questionnaire that runs after recording stops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

VideoType = Literal["highlights", "commentary", "tutorial", "short"]
Audience = Literal["beginners", "casual", "hardcore"]
Tone = Literal["energetic", "chill", "educational", "funny"]


@dataclass
class SessionProfile:
    game_name: str = ""
    channel_name: str = ""
    video_type: VideoType = "highlights"
    audience: Audience = "casual"
    tone: Tone = "energetic"
    target_length_minutes: int = 10
    special_moments: str = ""
    extra_context: str = ""

    @property
    def video_type_label(self) -> str:
        labels = {
            "highlights": "Highlights Reel (2-5 min, best moments only)",
            "commentary": "Full Commentary (10-30 min, full session)",
            "tutorial": "Tutorial / Guide (educational, tips-focused)",
            "short": "YouTube Short (60 seconds, vertical)",
        }
        return labels[self.video_type]

    @property
    def default_length(self) -> int:
        defaults = {
            "highlights": 4,
            "commentary": 15,
            "tutorial": 12,
            "short": 1,
        }
        return defaults[self.video_type]


def run_interview(session_duration_seconds: float | None = None) -> SessionProfile:
    """Run the interactive interview. Returns a filled SessionProfile."""
    profile = SessionProfile()

    console.print()
    console.print(Panel(
        Text("AI Video Editor — Session Setup", style="bold cyan", justify="center"),
        subtitle="Answer a few questions and I'll handle the rest",
    ))
    console.print()

    if session_duration_seconds:
        mins = int(session_duration_seconds // 60)
        secs = int(session_duration_seconds % 60)
        console.print(f"  Recorded session: [bold green]{mins}m {secs}s[/bold green]\n")

    # Game name
    profile.game_name = questionary.text(
        "What game were you playing?",
        validate=lambda v: bool(v.strip()) or "Please enter a game name",
    ).ask() or ""

    # Channel name
    profile.channel_name = questionary.text(
        "Your YouTube channel name (for branding):",
        default="My Gaming Channel",
    ).ask() or "My Gaming Channel"

    # Video type
    video_type_choice = questionary.select(
        "What type of video do you want?",
        choices=[
            questionary.Choice("Highlights Reel  — best moments, 2–5 min", value="highlights"),
            questionary.Choice("Full Commentary  — full session with narration, 10–30 min", value="commentary"),
            questionary.Choice("Tutorial / Guide — tips-focused, educational", value="tutorial"),
            questionary.Choice("YouTube Short    — 60-second vertical clip", value="short"),
        ],
    ).ask()
    profile.video_type = video_type_choice or "highlights"

    # Target audience
    audience_choice = questionary.select(
        "Who is your target audience?",
        choices=[
            questionary.Choice("Beginners  — new to this game", value="beginners"),
            questionary.Choice("Casual     — plays occasionally, wants entertainment", value="casual"),
            questionary.Choice("Hardcore   — experienced players, deep knowledge", value="hardcore"),
        ],
    ).ask()
    profile.audience = audience_choice or "casual"

    # Tone
    tone_choice = questionary.select(
        "What tone / vibe?",
        choices=[
            questionary.Choice("Energetic / Hype  — fast cuts, hype music", value="energetic"),
            questionary.Choice("Chill / Relaxed   — laid-back, slower pacing", value="chill"),
            questionary.Choice("Educational       — clear explanations, pause-and-explain", value="educational"),
            questionary.Choice("Funny / Meme-y    — comedic timing, reaction moments", value="funny"),
        ],
    ).ask()
    profile.tone = tone_choice or "energetic"

    # Target length (skipped for Shorts)
    if profile.video_type != "short":
        length_str = questionary.text(
            f"Target video length in minutes? (default: {profile.default_length})",
            default=str(profile.default_length),
            validate=lambda v: v.isdigit() or "Enter a number",
        ).ask()
        profile.target_length_minutes = int(length_str) if length_str and length_str.isdigit() else profile.default_length
    else:
        profile.target_length_minutes = 1

    # Special moments
    profile.special_moments = questionary.text(
        "Any specific moments to make sure we include? (optional — describe or leave blank)",
        default="",
    ).ask() or ""

    # Extra context
    profile.extra_context = questionary.text(
        "Anything else the AI should know? (optional — e.g. 'first time playing', 'ranked match')",
        default="",
    ).ask() or ""

    console.print()
    console.print(Panel(
        f"[bold]Game:[/bold] {profile.game_name}\n"
        f"[bold]Type:[/bold] {profile.video_type_label}\n"
        f"[bold]Audience:[/bold] {profile.audience}  |  [bold]Tone:[/bold] {profile.tone}\n"
        f"[bold]Length:[/bold] {'~60 seconds (Short)' if profile.video_type == 'short' else f'~{profile.target_length_minutes} minutes'}",
        title="[cyan]Your session profile[/cyan]",
    ))
    console.print()

    confirmed = questionary.confirm("Looks good? Start processing?", default=True).ask()
    if not confirmed:
        console.print("[yellow]Re-running interview...[/yellow]\n")
        return run_interview(session_duration_seconds)

    return profile
