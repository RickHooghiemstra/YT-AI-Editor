"""
Main pipeline orchestrator. Coordinates all stages from raw recordings to upload.
Uses Claude as the AI brain across analysis, scripting, and metadata stages.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agents.analyzer import analyze_footage, AnalysisResult
from src.agents.scriptwriter import generate_script, generate_metadata, VideoScript, VideoMetadata
from src.modules.recorder import RecordingSession
from src.modules.transcriber import transcribe, Transcript
from src.modules.video_editor import edit_video
from src.modules.thumbnail import generate_thumbnail
from src.modules.youtube_uploader import upload_to_youtube, select_title_interactively
from src.prompts.interview import run_interview, SessionProfile
from src.utils.config import get_settings
from src.utils.file_manager import save_json, get_session_dir

console = Console()


class Pipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.ensure_dirs()

    def run_from_session(self, recording: RecordingSession) -> Optional[str]:
        """Full pipeline from a completed recording session. Returns YouTube URL or None."""
        self._print_header("Processing recording")

        session_dir = recording.session_dir

        # 1. Transcribe audio
        console.rule("[cyan]Step 1/6 — Transcribe[/cyan]")
        transcript_cache = session_dir / "transcript.json"
        if transcript_cache.exists():
            console.print("[dim]Loading cached transcript...[/dim]")
            transcript = Transcript.load(transcript_cache)
        else:
            transcript = transcribe(recording.audio_file)
            transcript.save(transcript_cache)

        # 2. Interview user while analysis runs in background
        console.rule("[cyan]Step 2/6 — Session Interview[/cyan]")
        profile = run_interview(recording.duration_seconds)

        # 3. Analyze footage
        console.rule("[cyan]Step 3/6 — Analyze Footage[/cyan]")
        analysis_cache = session_dir / "analysis.json"
        if analysis_cache.exists():
            console.print("[dim]Loading cached analysis...[/dim]")
            analysis = _load_analysis(analysis_cache, session_dir)
        else:
            analysis = analyze_footage(
                screen_video=recording.screen_file,
                game_name=profile.game_name,
                audience=profile.audience,
            )
            _save_analysis(analysis, analysis_cache)

        self._print_analysis_summary(analysis)

        # 4. Generate script
        console.rule("[cyan]Step 4/6 — Generate Script[/cyan]")
        script = generate_script(profile, analysis, transcript)
        metadata = generate_metadata(profile, script, analysis)

        self._print_script_summary(script, metadata)

        # 5. Edit video
        console.rule("[cyan]Step 5/6 — Edit Video[/cyan]")
        output_filename = f"{profile.game_name.lower().replace(' ', '_')}_{recording.session_id}.mp4"
        output_path = self.settings.videos_dir / output_filename
        thumbnail_path = self.settings.thumbnails_dir / output_filename.replace(".mp4", "_thumb.jpg")

        is_short = profile.video_type == "short"
        edit_video(
            script=script,
            screen_video=recording.screen_file,
            webcam_video=recording.webcam_file,
            output_path=output_path,
            is_short=is_short,
        )

        # 6. Generate thumbnail
        generate_thumbnail(
            key_frames_dir=analysis.key_frames_dir,
            recommended_frame_index=analysis.recommended_thumbnail_frame,
            webcam_video=recording.webcam_file,
            title_text=metadata.thumbnail_text,
            subtext=metadata.thumbnail_subtext,
            tone=profile.tone,
            output_path=thumbnail_path,
        )

        # Save metadata to disk
        meta_path = self.settings.metadata_dir / output_filename.replace(".mp4", "_meta.json")
        save_json(meta_path, metadata.to_dict())

        # 7. Upload to YouTube
        console.rule("[cyan]Step 6/6 — YouTube Upload[/cyan]")
        self._print_upload_summary(output_path, metadata)

        upload = questionary.confirm("Upload this video to YouTube now?", default=True).ask()
        if not upload:
            console.print(f"[yellow]Skipped upload.[/yellow] Video saved to: {output_path}")
            return None

        privacy = questionary.select(
            "Upload privacy setting:",
            choices=[
                questionary.Choice("Private   — only you can see", value="private"),
                questionary.Choice("Unlisted  — anyone with the link", value="unlisted"),
                questionary.Choice("Public    — visible to everyone", value="public"),
            ],
        ).ask() or "private"

        title_idx = select_title_interactively(metadata)
        url = upload_to_youtube(output_path, thumbnail_path, metadata, title_idx, privacy)

        self._print_done(url, output_path, thumbnail_path)
        return url

    def run_from_files(
        self,
        screen_file: Path,
        webcam_file: Path,
        audio_file: Path,
        session_id: str = "manual",
    ) -> Optional[str]:
        """Run pipeline on pre-existing recordings (e.g. from OBS or folder watch)."""
        from src.modules.recorder import RecordingSession
        session_dir = screen_file.parent
        recording = RecordingSession(
            session_id=session_id,
            session_dir=session_dir,
            screen_file=screen_file,
            webcam_file=webcam_file,
            audio_file=audio_file,
            end_time=time.time(),
        )
        return self.run_from_session(recording)

    def _print_header(self, title: str) -> None:
        console.print()
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", title="YT AI Editor"))
        console.print()

    def _print_analysis_summary(self, analysis: AnalysisResult) -> None:
        top = analysis.top_moments(5)
        table = Table(title="Top Moments", show_header=True, header_style="bold cyan")
        table.add_column("Time", style="green", width=10)
        table.add_column("Score", width=7)
        table.add_column("Category", width=12)
        table.add_column("Description")
        for m in top:
            table.add_row(
                f"{m.timestamp_seconds:.0f}s",
                f"{m.highlight_score}/10",
                m.category,
                m.description[:60],
            )
        console.print(table)
        console.print(f"\n[dim]{analysis.session_summary}[/dim]\n")

    def _print_script_summary(self, script: VideoScript, metadata: VideoMetadata) -> None:
        console.print(Panel(
            "\n".join(f"  {i+1}. {t['title']}  [{t['style']}]" for i, t in enumerate(metadata.titles)),
            title="[cyan]Generated Titles[/cyan]",
        ))
        console.print(f"  Segments: {len(script.segments)}")
        console.print(f"  Est. duration: {script.estimated_duration_seconds:.0f}s")
        console.print()

    def _print_upload_summary(self, video_path: Path, metadata: VideoMetadata) -> None:
        size_mb = video_path.stat().st_size / 1024 / 1024
        console.print(Panel(
            f"[bold]File:[/bold] {video_path.name} ({size_mb:.1f} MB)\n"
            f"[bold]Tags:[/bold] {', '.join(metadata.tags[:8])}\n"
            f"[bold]Description preview:[/bold]\n{metadata.description[:200]}...",
            title="[cyan]Upload Preview[/cyan]",
        ))

    def _print_done(self, url: str, video: Path, thumb: Path) -> None:
        console.print()
        console.print(Panel(
            f"[bold green]Video uploaded![/bold green]\n\n"
            f"URL: [link={url}]{url}[/link]\n"
            f"Local: {video}\n"
            f"Thumbnail: {thumb}",
            title="Done",
        ))


def _save_analysis(analysis: AnalysisResult, path: Path) -> None:
    data = {
        "session_summary": analysis.session_summary,
        "best_clip_start": analysis.best_clip_start,
        "best_clip_end": analysis.best_clip_end,
        "recommended_thumbnail_frame": analysis.recommended_thumbnail_frame,
        "moments": [
            {
                "frame_index": m.frame_index,
                "timestamp_seconds": m.timestamp_seconds,
                "description": m.description,
                "energy": m.energy,
                "highlight_score": m.highlight_score,
                "category": m.category,
                "include_in_highlights": m.include_in_highlights,
            }
            for m in analysis.moments
        ],
    }
    save_json(path, data)


def _load_analysis(path: Path, session_dir: Path) -> AnalysisResult:
    from src.agents.analyzer import AnalysisResult, Moment
    data = json.loads(path.read_text())
    moments = [
        Moment(
            frame_index=m["frame_index"],
            timestamp_seconds=m["timestamp_seconds"],
            description=m["description"],
            energy=m["energy"],
            highlight_score=m["highlight_score"],
            category=m["category"],
            include_in_highlights=m["include_in_highlights"],
        )
        for m in data["moments"]
    ]
    return AnalysisResult(
        moments=moments,
        session_summary=data["session_summary"],
        best_clip_start=data["best_clip_start"],
        best_clip_end=data["best_clip_end"],
        recommended_thumbnail_frame=data["recommended_thumbnail_frame"],
        key_frames_dir=session_dir / "key_frames",
    )
