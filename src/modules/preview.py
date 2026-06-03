"""
Opens the rendered video in the system's media player before the upload prompt.
Tries mpv → vlc → xdg-open on Linux, `open` on macOS, `start` on Windows.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import questionary
from rich.console import Console

console = Console()


def preview_video(video_path: Path) -> bool:
    """
    Open video in a media player and ask the user if they want to proceed.
    Returns True to continue with upload, False to abort.
    """
    if not video_path.exists():
        console.print(f"[yellow]Preview skipped — file not found: {video_path}[/yellow]")
        return True

    size_mb = video_path.stat().st_size / 1024 / 1024
    console.print(f"\n[cyan]Opening preview:[/cyan] {video_path.name}  ({size_mb:.1f} MB)")

    player = _find_player()
    if player:
        try:
            subprocess.Popen(
                [player, str(video_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            console.print(f"[dim]Opened in {player}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Could not open player: {e}[/yellow]")
    else:
        console.print(
            f"[yellow]No media player found.[/yellow] Open manually:\n  {video_path}"
        )

    proceed = questionary.select(
        "How does it look?",
        choices=[
            questionary.Choice("Looks good — proceed with upload", value="upload"),
            questionary.Choice("Looks good — save locally, skip upload for now", value="skip"),
            questionary.Choice("Something is wrong — abort", value="abort"),
        ],
    ).ask()

    if proceed == "upload":
        return True
    if proceed == "skip":
        console.print(f"[yellow]Upload skipped.[/yellow] Video saved at: {video_path}")
        return False
    # abort
    console.print("[red]Aborted by user.[/red]")
    raise SystemExit(0)


def _find_player() -> str | None:
    if sys.platform == "linux":
        for player in ["mpv", "vlc", "totem", "xdg-open"]:
            if shutil.which(player):
                return player
    elif sys.platform == "darwin":
        return "open"
    elif sys.platform == "win32":
        return "start"
    return None
