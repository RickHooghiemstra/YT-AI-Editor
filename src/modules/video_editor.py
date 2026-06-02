"""
Video editing engine: composites gameplay + webcam, applies cuts, captions,
speed changes, and assembles the final video using MoviePy + FFmpeg.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from src.agents.scriptwriter import VideoScript, VideoSegment
from src.utils.config import get_settings

console = Console()

# Webcam overlay dimensions and position (bottom-left corner)
WEBCAM_W = 320
WEBCAM_H = 180
WEBCAM_X = 20
WEBCAM_Y_FROM_BOTTOM = 20

# Shorts dimensions
SHORTS_W = 1080
SHORTS_H = 1920


def edit_video(
    script: VideoScript,
    screen_video: Path,
    webcam_video: Path,
    output_path: Path,
    is_short: bool = False,
    use_avatar: bool = True,
) -> Path:
    """
    Assemble the final video from script + raw recordings.
    Returns the path to the finished video.
    """
    settings = get_settings()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print("[cyan]Starting video assembly...[/cyan]")
    console.print(f"  Segments: {len(script.segments)}")
    console.print(f"  Estimated duration: {script.estimated_duration_seconds:.0f}s")

    # Apply caricature filter to webcam before compositing
    active_webcam = webcam_video
    if use_avatar and webcam_video.exists():
        from src.modules.avatar import AvatarProcessor
        avatar = AvatarProcessor(baseline_dir=webcam_video.parent.parent)
        caricature_path = webcam_video.parent / f"caricature_{webcam_video.name}"
        if not caricature_path.exists():
            active_webcam = avatar.process_video(webcam_video, caricature_path)
        else:
            console.print("[dim]Using cached caricature webcam[/dim]")
            active_webcam = caricature_path

    if is_short:
        return _edit_short(script, screen_video, active_webcam, output_path)
    else:
        return _edit_standard(script, screen_video, active_webcam, output_path)


def _edit_standard(
    script: VideoScript,
    screen_video: Path,
    webcam_video: Path,
    output_path: Path,
) -> Path:
    """Landscape video: gameplay full screen + webcam overlay bottom-left."""
    try:
        from moviepy.editor import (
            VideoFileClip,
            CompositeVideoClip,
            concatenate_videoclips,
            TextClip,
        )
    except ImportError:
        raise ImportError("moviepy not installed. Run: pip install moviepy")

    screen_clip = VideoFileClip(str(screen_video))
    webcam_clip = VideoFileClip(str(webcam_video))

    segment_clips = []
    for seg in script.segments:
        # Clamp timestamps to actual video length
        start = min(seg.source_start, screen_clip.duration - 1)
        end = min(seg.source_end, screen_clip.duration)
        if end <= start:
            continue

        gameplay = screen_clip.subclip(start, end)

        # Apply speed multiplier
        if abs(seg.speed_multiplier - 1.0) > 0.01:
            gameplay = gameplay.speedx(seg.speed_multiplier)

        # Webcam overlay
        if seg.include_webcam and webcam_clip.duration > 0:
            wc_start = min(start, webcam_clip.duration - 1)
            wc_end = min(end, webcam_clip.duration)
            if wc_end > wc_start:
                wc = (
                    webcam_clip.subclip(wc_start, wc_end)
                    .resize(height=WEBCAM_H)
                    .set_position((WEBCAM_X, gameplay.size[1] - WEBCAM_H - WEBCAM_Y_FROM_BOTTOM))
                )
                if abs(seg.speed_multiplier - 1.0) > 0.01:
                    wc = wc.speedx(seg.speed_multiplier)
                gameplay = CompositeVideoClip([gameplay, wc])

        # Caption overlay
        if seg.caption:
            try:
                caption = (
                    TextClip(
                        seg.caption,
                        fontsize=40,
                        color="white",
                        stroke_color="black",
                        stroke_width=2,
                        method="label",
                    )
                    .set_position(("center", 0.85), relative=True)
                    .set_duration(gameplay.duration)
                )
                gameplay = CompositeVideoClip([gameplay, caption])
            except Exception:
                pass  # TextClip requires ImageMagick; skip caption if unavailable

        segment_clips.append(gameplay)

    if not segment_clips:
        raise ValueError("No valid segments to assemble")

    final = concatenate_videoclips(segment_clips, method="compose")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("Rendering final video...", total=None)
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None,
            threads=4,
            bitrate="5000k",
        )

    screen_clip.close()
    webcam_clip.close()
    console.print(f"[green]Video rendered:[/green] {output_path}")
    return output_path


def _edit_short(
    script: VideoScript,
    screen_video: Path,
    webcam_video: Path,
    output_path: Path,
) -> Path:
    """
    YouTube Short: vertical 9:16 format.
    Top half = webcam, bottom half = gameplay (cropped to square).
    """
    try:
        from moviepy.editor import VideoFileClip, CompositeVideoClip, concatenate_videoclips
    except ImportError:
        raise ImportError("moviepy not installed")

    screen_clip = VideoFileClip(str(screen_video))
    webcam_clip = VideoFileClip(str(webcam_video))

    half_h = SHORTS_H // 2
    short_w = SHORTS_W

    gameplay_clip = screen_clip.subclip(0, min(58, screen_clip.duration))
    wc_clip = webcam_clip.subclip(0, min(58, webcam_clip.duration))

    # Scale gameplay to fill top half
    gameplay_scaled = gameplay_clip.resize(width=short_w)
    wc_scaled = wc_clip.resize(width=short_w)

    # Composite vertically
    gameplay_positioned = gameplay_scaled.set_position((0, half_h))
    wc_positioned = wc_scaled.set_position((0, 0))

    final = CompositeVideoClip(
        [gameplay_positioned, wc_positioned],
        size=(short_w, SHORTS_H),
    ).subclip(0, min(58, gameplay_clip.duration))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("Rendering YouTube Short...", total=None)
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None,
            threads=4,
        )

    screen_clip.close()
    webcam_clip.close()
    console.print(f"[green]Short rendered:[/green] {output_path}")
    return output_path
