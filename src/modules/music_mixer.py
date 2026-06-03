"""
Mixes mood-matched background music into a rendered video.

Music files live in music/<mood>/ (mp3 or wav).
Picks a random track, loops if needed, applies 2s fade-in / 3s fade-out,
mixes at low volume (default 15%) under the original audio.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

MUSIC_DIR = Path("music")
CREDITS_FILE = MUSIC_DIR / "CREDITS.txt"
DEFAULT_VOLUME = 0.15
FADE_IN_SECONDS = 2.0
FADE_OUT_SECONDS = 3.0
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


def mix_music(
    video_path: Path,
    output_path: Path,
    mood: str,
    volume: float = DEFAULT_VOLUME,
) -> Path:
    """
    Add background music to a video file.
    Returns output_path (with music) or video_path (if no music available).
    """
    track = _pick_track(mood)
    if track is None:
        console.print(
            f"[dim]No music found in music/{mood}/ — skipping background music.[/dim]\n"
            f"[dim]Drop MP3/WAV files there to enable. See music/README.md.[/dim]"
        )
        return video_path

    console.print(f"[cyan]Mixing background music:[/cyan] {track.name}  (mood: {mood}, vol: {volume*100:.0f}%)")

    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
    except ImportError:
        raise ImportError("moviepy not installed. Run: pip install moviepy")

    video = VideoFileClip(str(video_path))
    music_raw = AudioFileClip(str(track))

    # Loop music to cover full video duration
    if music_raw.duration < video.duration:
        from moviepy.editor import concatenate_audioclips
        repeats = int(video.duration / music_raw.duration) + 2
        music_raw = concatenate_audioclips([music_raw] * repeats)

    music = (
        music_raw
        .subclip(0, video.duration)
        .volumex(volume)
        .audio_fadein(FADE_IN_SECONDS)
        .audio_fadeout(FADE_OUT_SECONDS)
    )

    if video.audio is not None:
        mixed_audio = CompositeAudioClip([video.audio, music])
    else:
        mixed_audio = music

    final = video.set_audio(mixed_audio)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("Rendering with music...", total=None)
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=video.fps,
            logger=None,
            threads=4,
        )

    video.close()
    music_raw.close()
    console.print(f"[green]Music mixed:[/green] {output_path.name}")
    return output_path


def get_music_credits() -> str:
    """Return credits text if CREDITS.txt exists, else empty string."""
    if CREDITS_FILE.exists():
        return "\n\n" + CREDITS_FILE.read_text().strip()
    return ""


def _pick_track(mood: str) -> Optional[Path]:
    """Pick a random track from the mood subfolder, with fallback to any mood."""
    mood_dir = MUSIC_DIR / mood
    track = _random_track_from(mood_dir)
    if track:
        return track

    # Fallback: try any mood folder
    for subfolder in MUSIC_DIR.iterdir():
        if subfolder.is_dir():
            track = _random_track_from(subfolder)
            if track:
                return track

    return None


def _random_track_from(directory: Path) -> Optional[Path]:
    if not directory.exists():
        return None
    tracks = [
        f for f in directory.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return random.choice(tracks) if tracks else None


def dominant_mood(moods: list[str]) -> str:
    """Return the most common mood from a list of segment moods."""
    if not moods:
        return "energetic"
    return max(set(moods), key=moods.count)
