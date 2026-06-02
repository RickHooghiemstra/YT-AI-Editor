"""
Analyzes gameplay footage using Claude Vision.
Extracts key frames, scores each for highlight value, identifies moments.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn

from src.prompts.templates import ANALYZER_SYSTEM, ANALYZER_FRAMES_PROMPT
from src.utils.config import get_settings

console = Console()


@dataclass
class Moment:
    frame_index: int
    timestamp_seconds: float
    description: str
    energy: str
    highlight_score: int
    category: str
    include_in_highlights: bool


@dataclass
class AnalysisResult:
    moments: list[Moment]
    session_summary: str
    best_clip_start: float
    best_clip_end: float
    recommended_thumbnail_frame: int
    key_frames_dir: Path

    def top_moments(self, n: int = 10) -> list[Moment]:
        return sorted(self.moments, key=lambda m: m.highlight_score, reverse=True)[:n]

    def highlight_moments(self) -> list[Moment]:
        return [m for m in self.moments if m.include_in_highlights]

    def to_summary_text(self) -> str:
        top = self.top_moments(5)
        lines = [self.session_summary, "\nTop moments:"]
        for m in top:
            lines.append(
                f"  [{m.timestamp_seconds:.1f}s] {m.description} "
                f"(score: {m.highlight_score}/10, {m.energy})"
            )
        return "\n".join(lines)


def analyze_footage(
    screen_video: Path,
    game_name: str,
    audience: str,
    frames_per_minute: int = 2,
) -> AnalysisResult:
    """
    Extract key frames from gameplay video and analyze with Claude Vision.
    frames_per_minute: how many frames to sample per minute of footage.
    """
    settings = get_settings()
    key_frames_dir = screen_video.parent / "key_frames"
    key_frames_dir.mkdir(exist_ok=True)

    frames, timestamps = _extract_frames(screen_video, frames_per_minute, key_frames_dir)
    console.print(f"[cyan]Extracted {len(frames)} key frames for analysis[/cyan]")

    duration = timestamps[-1] if timestamps else 0
    result = _analyze_with_claude(
        frames=frames,
        timestamps=timestamps,
        game_name=game_name,
        audience=audience,
        duration=duration,
        key_frames_dir=key_frames_dir,
    )
    return result


def _extract_frames(
    video_path: Path,
    frames_per_minute: int,
    output_dir: Path,
) -> tuple[list[Path], list[float]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps

    interval_frames = max(1, int(fps * 60 / frames_per_minute))

    frame_paths = []
    timestamps = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting frames...", total=total_frames)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % interval_frames == 0:
                timestamp = frame_idx / fps
                frame_path = output_dir / f"frame_{frame_idx:06d}_{timestamp:.1f}s.jpg"
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_paths.append(frame_path)
                timestamps.append(timestamp)

            frame_idx += 1
            progress.update(task, advance=1)

    cap.release()
    console.print(f"[green]Extracted {len(frame_paths)} frames[/green] from {duration_seconds:.1f}s video")
    return frame_paths, timestamps


def _analyze_with_claude(
    frames: list[Path],
    timestamps: list[float],
    game_name: str,
    audience: str,
    duration: float,
    key_frames_dir: Path,
) -> AnalysisResult:
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Process in batches of 10 frames (Claude Vision limit per call)
    all_moments: list[Moment] = []
    batch_size = 10

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Analyzing frames with Claude Vision...",
            total=len(frames),
        )

        for batch_start in range(0, len(frames), batch_size):
            batch_frames = frames[batch_start: batch_start + batch_size]
            batch_timestamps = timestamps[batch_start: batch_start + batch_size]

            content: list[Any] = []
            for i, (fp, ts) in enumerate(zip(batch_frames, batch_timestamps)):
                img_b64 = base64.b64encode(fp.read_bytes()).decode()
                content.append({
                    "type": "text",
                    "text": f"Frame {batch_start + i} at {ts:.1f}s:",
                })
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    },
                })

            content.append({
                "type": "text",
                "text": ANALYZER_FRAMES_PROMPT.format(
                    game_name=game_name,
                    duration=f"{int(duration // 60)}m {int(duration % 60)}s",
                    audience=audience,
                ),
            })

            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                system=ANALYZER_SYSTEM,
                messages=[{"role": "user", "content": content}],
            )

            raw = response.content[0].text
            parsed = _parse_analysis_json(raw, batch_start, batch_timestamps)
            all_moments.extend(parsed)
            progress.update(task, advance=len(batch_frames))

    # Generate overall summary with a final call
    summary_data = _generate_summary(all_moments, game_name, duration, client, settings)

    return AnalysisResult(
        moments=all_moments,
        session_summary=summary_data.get("session_summary", "Gaming session analyzed."),
        best_clip_start=summary_data.get("best_clip_start", 0.0),
        best_clip_end=summary_data.get("best_clip_end", min(duration, 300.0)),
        recommended_thumbnail_frame=summary_data.get("recommended_thumbnail_frame", 0),
        key_frames_dir=key_frames_dir,
    )


def _parse_analysis_json(raw: str, batch_offset: int, timestamps: list[float]) -> list[Moment]:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(raw[start:end])
        moments = []
        for m in data.get("moments", []):
            moments.append(Moment(
                frame_index=m.get("frame_index", 0) + batch_offset,
                timestamp_seconds=m.get("timestamp_seconds", timestamps[0] if timestamps else 0),
                description=m.get("description", ""),
                energy=m.get("energy", "medium"),
                highlight_score=int(m.get("highlight_score", 5)),
                category=m.get("category", "general"),
                include_in_highlights=bool(m.get("include_in_highlights", False)),
            ))
        return moments
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def _generate_summary(
    moments: list[Moment],
    game_name: str,
    duration: float,
    client: Any,
    settings: Any,
) -> dict:
    top = sorted(moments, key=lambda m: m.highlight_score, reverse=True)[:5]
    moments_text = "\n".join(
        f"- [{m.timestamp_seconds:.1f}s] {m.description} (score: {m.highlight_score})"
        for m in top
    )
    prompt = (
        f"Game: {game_name}, Duration: {duration:.0f}s\n"
        f"Top moments:\n{moments_text}\n\n"
        "Return JSON: {\"session_summary\": \"...\", \"best_clip_start\": 0.0, "
        "\"best_clip_end\": 0.0, \"recommended_thumbnail_frame\": 0}"
    )
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {
            "session_summary": f"Gaming session of {game_name}.",
            "best_clip_start": 0.0,
            "best_clip_end": min(duration, 300.0),
            "recommended_thumbnail_frame": 0,
        }
