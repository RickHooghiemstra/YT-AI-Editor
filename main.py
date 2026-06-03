#!/usr/bin/env python3
"""
YT AI Editor — Main CLI entry point.

Commands:
  record   — Start the hotkey daemon (Ctrl+Shift+R to start/stop recording)
  process  — Run the pipeline on existing recording files
  pipeline — Record + auto-process when you stop (all-in-one)
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path
from typing import Optional

import questionary

import typer
from rich.console import Console

app = typer.Typer(
    name="ytai",
    help="AI-powered gaming video creator — record, edit, and upload automatically.",
    add_completion=False,
)
console = Console()


@app.command()
def record(
    hotkey: str = typer.Option(
        "<ctrl>+<shift>+r",
        "--hotkey", "-k",
        help="Global hotkey to toggle recording",
    ),
    auto_process: bool = typer.Option(
        False,
        "--auto-process", "-a",
        help="Automatically run the full pipeline when recording stops",
    ),
) -> None:
    """
    Start the hotkey daemon. Press the hotkey in-game to start/stop recording.
    Press Ctrl+C in this terminal to quit.
    """
    from src.modules.recorder import Recorder, run_hotkey_daemon
    from src.agents.orchestrator import Pipeline
    from src.utils.config import get_settings

    get_settings().ensure_dirs()

    if auto_process:
        _run_with_auto_process(hotkey)
    else:
        run_hotkey_daemon(hotkey)


@app.command()
def process(
    screen: Path = typer.Argument(..., help="Path to screen recording"),
    webcam: Path = typer.Argument(..., help="Path to webcam recording"),
    audio: Path = typer.Argument(..., help="Path to audio recording"),
    session_id: str = typer.Option("manual", "--session-id", "-s"),
) -> None:
    """Process existing recording files through the full pipeline."""
    from src.agents.orchestrator import Pipeline
    from src.utils.config import get_settings

    get_settings().ensure_dirs()

    for f in [screen, webcam, audio]:
        if not f.exists():
            console.print(f"[red]File not found: {f}[/red]")
            raise typer.Exit(1)

    pipeline = Pipeline()
    pipeline.run_from_files(screen, webcam, audio, session_id)


@app.command()
def pipeline(
    hotkey: str = typer.Option(
        "<ctrl>+<shift>+r",
        "--hotkey", "-k",
        help="Global hotkey to toggle recording",
    ),
) -> None:
    """
    All-in-one: starts hotkey daemon and automatically processes after each recording.
    Press hotkey to start gaming, press again when done — the AI handles everything.
    """
    _run_with_auto_process(hotkey)


@app.command(name="quick-clip")
def quick_clip(
    screen: Path = typer.Argument(..., help="Screen recording"),
    webcam: Path = typer.Argument(..., help="Webcam recording"),
    session_id: str = typer.Option("quick", "--session-id", "-s"),
) -> None:
    """
    Fast highlights reel — no transcription, vision-only.
    2 questions, ~5 minute runtime. Great for quick posts.
    """
    from src.agents.orchestrator import Pipeline
    from src.utils.config import get_settings

    get_settings().ensure_dirs()
    for f in [screen, webcam]:
        if not f.exists():
            console.print(f"[red]File not found: {f}[/red]")
            raise typer.Exit(1)

    Pipeline().run_quick_clip(screen, webcam, session_id)


@app.command(name="best-of")
def best_of(
    game: Optional[str] = typer.Option(None, "--game", "-g", help="Filter by game name"),
    days: Optional[int] = typer.Option(7, "--days", "-d", help="Look back N days (0 = all time)"),
    channel: str = typer.Option("My Gaming Channel", "--channel", "-c"),
    min_score: int = typer.Option(7, "--min-score", help="Minimum highlight score 1-10"),
) -> None:
    """
    Compile a best-of video from your clip library.
    Pulls top-scored highlights from past sessions without re-analyzing anything.
    """
    from src.agents.orchestrator import Pipeline
    from src.utils.config import get_settings

    get_settings().ensure_dirs()
    look_back = days if days and days > 0 else None
    Pipeline().run_best_of(game=game, days=look_back, channel_name=channel, min_score=min_score)


@app.command(name="library")
def library_summary() -> None:
    """Show a summary of all clips saved in the clip library."""
    from src.modules.clip_library import get_library
    get_library().summary()


@app.command()
def calibrate(
    photo: Path = typer.Argument(..., help="Path to a photo of your face (neutral expression, good lighting)"),
) -> None:
    """
    Calibrate the avatar filter to YOUR face.
    Run this once with a selfie — the system learns your neutral expression
    so exaggeration is accurate relative to you specifically.
    """
    from src.modules.avatar import AvatarProcessor
    from src.utils.config import get_settings

    if not photo.exists():
        console.print(f"[red]Photo not found: {photo}[/red]")
        raise typer.Exit(1)

    settings = get_settings()
    settings.ensure_dirs()
    processor = AvatarProcessor(baseline_dir=settings.recordings_dir)
    baseline = processor.calibrate_from_photo(photo)
    console.print(
        "\n[green]Done![/green] Your face baseline is saved. "
        "The caricature filter will now exaggerate relative to YOUR neutral face.\n"
        "Run [bold]ytai avatar-preview[/bold] to see it live before recording."
    )


@app.command(name="avatar-preview")
def avatar_preview(
    device: int = typer.Option(0, "--device", "-d", help="Webcam device index"),
    exaggeration: float = typer.Option(2.5, "--exaggeration", "-e", help="Exaggeration multiplier (1.0 = none, 3.0 = extreme)"),
    cartoon: float = typer.Option(0.75, "--cartoon", "-c", help="Cartoon shader strength 0.0-1.0"),
) -> None:
    """
    Live preview of the caricature avatar using your webcam.
    Shows Original | Caricature side by side. Press Q to quit.
    Use this to tune the exaggeration before a recording session.
    """
    from src.modules.avatar import AvatarProcessor
    from src.utils.config import get_settings

    settings = get_settings()
    processor = AvatarProcessor(
        exaggeration=exaggeration,
        cartoon_strength=cartoon,
        baseline_dir=settings.recordings_dir,
    )
    processor.preview_live(device)


@app.command()
def setup() -> None:
    """Interactive first-time setup: configure API keys and check dependencies."""
    from src.utils.config import get_settings

    console.print("\n[bold cyan]YT AI Editor — Setup[/bold cyan]\n")

    _check_dependencies()
    _check_env_file()

    console.print("\n[green]Setup complete![/green] Run [bold]ytai pipeline[/bold] to get started.\n")


def _run_with_auto_process(hotkey: str) -> None:
    """Hotkey daemon that auto-triggers the pipeline after each recording stop."""
    from pynput import keyboard

    from src.modules.recorder import Recorder, _parse_hotkey, _matches
    from src.agents.orchestrator import Pipeline

    recorder = Recorder()
    pipeline = Pipeline()
    combo = _parse_hotkey(hotkey)
    currently_pressed: set = set()

    def on_press(key):
        currently_pressed.add(key)
        if _matches(currently_pressed, combo):
            if recorder.is_recording:
                session = recorder.stop()
                # Run pipeline in a thread so hotkey stays responsive
                t = threading.Thread(target=pipeline.run_from_session, args=(session,), daemon=True)
                t.start()
            else:
                recorder.start()

    def on_release(key):
        currently_pressed.discard(key)

    console.print(
        f"\n[cyan]Pipeline daemon ready[/cyan] — "
        f"press [bold]{hotkey}[/bold] to start/stop recording.\n"
        "The AI will automatically process and upload when you stop.\n"
        "Press [bold]Ctrl+C[/bold] to exit.\n"
    )

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            if recorder.is_recording:
                recorder.stop()
            console.print("[yellow]Exited.[/yellow]")


def _check_dependencies() -> None:
    import shutil

    deps = {
        "ffmpeg": "FFmpeg (video recording/editing)",
        "python3": "Python 3",
    }
    for cmd, label in deps.items():
        if shutil.which(cmd):
            console.print(f"  [green]✓[/green] {label}")
        else:
            console.print(f"  [red]✗[/red] {label} — install with your package manager")

    py_deps = [
        "anthropic", "faster_whisper", "moviepy", "cv2",
        "PIL", "pynput", "questionary", "rich",
        "googleapiclient", "mediapipe",
    ]
    for dep in py_deps:
        try:
            __import__(dep)
            console.print(f"  [green]✓[/green] {dep}")
        except ImportError:
            console.print(f"  [yellow]![/yellow] {dep} — run: pip install -r requirements.txt")


def _check_env_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        console.print("\n[yellow]No .env file found.[/yellow] Creating from template...")
        import shutil
        shutil.copy(".env.example", ".env")
        console.print("  Created [bold].env[/bold] — edit it and add your API keys.")
    else:
        console.print("\n  [green]✓[/green] .env file found")

    from src.utils.config import get_settings
    settings = get_settings()
    if not settings.anthropic_api_key:
        console.print("  [yellow]![/yellow] ANTHROPIC_API_KEY not set in .env")
    else:
        console.print("  [green]✓[/green] ANTHROPIC_API_KEY set")


if __name__ == "__main__":
    app()
