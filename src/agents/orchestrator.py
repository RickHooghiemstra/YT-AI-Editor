"""
Main pipeline orchestrator. Coordinates all stages from raw recordings to upload.
Includes quick-clip mode (no transcription, vision-only, ~5 min) and
best-of compilation from the clip library.
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
from src.agents.scriptwriter import (
    generate_script, generate_metadata, generate_best_of_metadata,
    VideoScript, VideoMetadata,
)
from src.modules.recorder import RecordingSession
from src.modules.transcriber import transcribe, Transcript
from src.modules.video_editor import edit_video
from src.modules.thumbnail import generate_thumbnail
from src.modules.youtube_uploader import upload_to_youtube, select_title_interactively
from src.modules.music_mixer import mix_music, dominant_mood
from src.modules.clip_library import get_library
from src.modules.preview import preview_video
from src.prompts.interview import run_interview, SessionProfile
from src.prompts.game_profiles import get_game_profile
from src.utils.config import get_settings
from src.utils.file_manager import save_json, get_session_dir

console = Console()


class Pipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.ensure_dirs()

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_from_session(self, recording: RecordingSession) -> Optional[str]:
        """Full pipeline from a completed recording. Returns YouTube URL or None."""
        self._print_header("Processing recording")

        session_dir = recording.session_dir

        # 1. Transcribe
        console.rule("[cyan]Step 1/7 — Transcribe[/cyan]")
        transcript_cache = session_dir / "transcript.json"
        if transcript_cache.exists():
            console.print("[dim]Loading cached transcript...[/dim]")
            transcript = Transcript.load(transcript_cache)
        else:
            transcript = transcribe(recording.audio_file)
            transcript.save(transcript_cache)

        # 2. Interview (while analysis could run, we need game name first)
        console.rule("[cyan]Step 2/7 — Session Interview[/cyan]")
        profile = run_interview(recording.duration_seconds)

        # 3. Analyze footage
        console.rule("[cyan]Step 3/7 — Analyze Footage[/cyan]")
        analysis_cache = session_dir / "analysis.json"
        if analysis_cache.exists():
            console.print("[dim]Loading cached analysis...[/dim]")
            analysis = _load_analysis(analysis_cache, session_dir)
        else:
            analysis = analyze_footage(
                screen_video=recording.screen_file,
                game_name=profile.game_name,
                audience=profile.audience,
                game_profile=get_game_profile(profile.game_name),
            )
            _save_analysis(analysis, analysis_cache)

        # Save to clip library
        get_library().add_session_highlights(
            session_id=recording.session_id,
            game=profile.game_name,
            screen_file=recording.screen_file,
            webcam_file=recording.webcam_file,
            moments=analysis.moments,
        )

        self._print_analysis_summary(analysis)

        # 4. Generate script + metadata
        console.rule("[cyan]Step 4/7 — Generate Script[/cyan]")
        script = generate_script(profile, analysis, transcript)
        metadata = generate_metadata(profile, script, analysis)

        self._print_script_summary(script, metadata)

        # 5. Edit video
        console.rule("[cyan]Step 5/7 — Edit Video[/cyan]")
        slug = profile.game_name.lower().replace(" ", "_")
        base_name = f"{slug}_{recording.session_id}"
        raw_video = self.settings.videos_dir / f"{base_name}_raw.mp4"
        output_path = self.settings.videos_dir / f"{base_name}.mp4"
        thumbnail_path = self.settings.thumbnails_dir / f"{base_name}_thumb.jpg"

        is_short = profile.video_type == "short"
        edit_video(
            script=script,
            screen_video=recording.screen_file,
            webcam_video=recording.webcam_file,
            output_path=raw_video,
            is_short=is_short,
        )

        # 6. Mix background music
        console.rule("[cyan]Step 6/7 — Music + Thumbnail[/cyan]")
        mood = script.dominant_mood
        final_video = mix_music(raw_video, output_path, mood)
        if final_video == raw_video:
            # No music was mixed — use raw as final
            raw_video.rename(output_path)

        generate_thumbnail(
            key_frames_dir=analysis.key_frames_dir,
            recommended_frame_index=analysis.recommended_thumbnail_frame,
            webcam_video=recording.webcam_file,
            title_text=metadata.thumbnail_text,
            subtext=metadata.thumbnail_subtext,
            tone=profile.tone,
            output_path=thumbnail_path,
        )

        # Save metadata
        meta_path = self.settings.metadata_dir / f"{base_name}_meta.json"
        save_json(meta_path, metadata.to_dict())

        # 7. Preview + upload
        console.rule("[cyan]Step 7/7 — Preview & Upload[/cyan]")
        should_upload = preview_video(output_path)
        if not should_upload:
            return None

        return self._upload(output_path, thumbnail_path, metadata)

    def run_from_files(
        self,
        screen_file: Path,
        webcam_file: Path,
        audio_file: Path,
        session_id: str = "manual",
    ) -> Optional[str]:
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

    # ------------------------------------------------------------------
    # Quick clip mode — no transcription, vision-only, ~5 min
    # ------------------------------------------------------------------

    def run_quick_clip(
        self,
        screen_file: Path,
        webcam_file: Path,
        session_id: str = "quick",
    ) -> Optional[str]:
        """
        Fast highlights reel using vision-only analysis.
        Skips transcription. Minimal interview (2 questions).
        Typical runtime: 5–8 minutes.
        """
        self._print_header("Quick Clip Mode")
        console.print("[dim]Skipping transcription — vision-only analysis[/dim]\n")

        import questionary as q

        game_name = q.text("What game were you playing?").ask() or "Unknown"
        tone = q.select(
            "Tone?",
            choices=[
                questionary.Choice("Energetic / Hype", value="energetic"),
                questionary.Choice("Funny", value="funny"),
                questionary.Choice("Chill", value="chill"),
            ],
        ).ask() or "energetic"

        console.rule("[cyan]Analyzing footage (vision only)...[/cyan]")
        session_dir = screen_file.parent
        analysis_cache = session_dir / "analysis_quick.json"

        game_profile = get_game_profile(game_name)
        if analysis_cache.exists():
            analysis = _load_analysis(analysis_cache, session_dir)
        else:
            analysis = analyze_footage(
                screen_video=screen_file,
                game_name=game_name,
                audience="casual",
                frames_per_minute=4,   # more frames to compensate for no transcript
                game_profile=game_profile,
                quick_mode=True,
            )
            _save_analysis(analysis, analysis_cache)

        get_library().add_session_highlights(
            session_id=session_id,
            game=game_name,
            screen_file=screen_file,
            webcam_file=webcam_file,
            moments=analysis.moments,
        )
        self._print_analysis_summary(analysis)

        # Build a simple script from top moments directly
        script = _script_from_top_moments(analysis, target_minutes=3)
        profile = _quick_profile(game_name, tone)
        metadata = generate_metadata(profile, script, analysis)

        self._print_script_summary(script, metadata)

        slug = game_name.lower().replace(" ", "_")
        base_name = f"{slug}_{session_id}_quick"
        raw_video = self.settings.videos_dir / f"{base_name}_raw.mp4"
        output_path = self.settings.videos_dir / f"{base_name}.mp4"
        thumbnail_path = self.settings.thumbnails_dir / f"{base_name}_thumb.jpg"

        edit_video(script=script, screen_video=screen_file, webcam_video=webcam_file,
                   output_path=raw_video, is_short=False)

        final_video = mix_music(raw_video, output_path, script.dominant_mood)
        if final_video == raw_video:
            raw_video.rename(output_path)

        generate_thumbnail(
            key_frames_dir=analysis.key_frames_dir,
            recommended_frame_index=analysis.recommended_thumbnail_frame,
            webcam_video=webcam_file,
            title_text=metadata.thumbnail_text,
            subtext=metadata.thumbnail_subtext,
            tone=tone,
            output_path=thumbnail_path,
        )

        should_upload = preview_video(output_path)
        if not should_upload:
            return None
        return self._upload(output_path, thumbnail_path, metadata)

    # ------------------------------------------------------------------
    # Best-of compilation from clip library
    # ------------------------------------------------------------------

    def run_best_of(
        self,
        game: Optional[str] = None,
        days: Optional[int] = 7,
        channel_name: str = "My Gaming Channel",
        min_score: int = 7,
    ) -> Optional[str]:
        """
        Compile a best-of video from the clip library.
        Pulls top-scored highlights across all sessions in the given window.
        """
        self._print_header("Best-Of Compilation")

        library = get_library()
        clips = library.query(game=game, days=days, min_score=min_score, limit=30)

        if not clips:
            console.print(
                f"[yellow]No clips found[/yellow] in the library "
                f"{'for ' + game if game else ''}"
                f"{' in the last ' + str(days) + ' days' if days else ''}.\n"
                "Record some sessions first, or lower --min-score."
            )
            return None

        game_label = game or "All Games"
        period = f"Last {days} days" if days else "All time"
        console.print(f"[cyan]Found {len(clips)} clips[/cyan] — {game_label}, {period}")

        # Show what we're working with
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Score", width=7)
        table.add_column("Game", width=14)
        table.add_column("Category", width=12)
        table.add_column("Description")
        for c in clips[:10]:
            table.add_row(str(c.highlight_score), c.game, c.category, c.description[:50])
        console.print(table)

        confirmed = questionary.confirm(
            f"Build a best-of video from these {len(clips)} clips?", default=True
        ).ask()
        if not confirmed:
            return None

        # Group clips by source session to minimize seeks
        from collections import defaultdict
        by_session: dict[str, list] = defaultdict(list)
        for clip in clips:
            by_session[clip.session_id].append(clip)

        # Build a script from clips
        script = _script_from_library_clips(clips)
        metadata = generate_best_of_metadata(
            game_name=game_label,
            channel_name=channel_name,
            period=period,
            clips=clips,
        )

        slug = (game or "bestof").lower().replace(" ", "_")
        import time as _time
        sid = int(_time.time())
        base_name = f"{slug}_bestof_{sid}"
        raw_video = self.settings.videos_dir / f"{base_name}_raw.mp4"
        output_path = self.settings.videos_dir / f"{base_name}.mp4"

        # Use first available webcam for thumbnail/overlay
        first_webcam = Path(clips[0].webcam_file)
        first_screen = Path(clips[0].screen_file)

        # Build video from first session's footage (simplified — uses top clip's source)
        edit_video(script=script, screen_video=first_screen, webcam_video=first_webcam,
                   output_path=raw_video, is_short=False)

        final_video = mix_music(raw_video, output_path, "energetic")
        if final_video == raw_video:
            raw_video.rename(output_path)

        thumbnail_path = self.settings.thumbnails_dir / f"{base_name}_thumb.jpg"
        analysis = _load_analysis(
            first_screen.parent / "analysis.json", first_screen.parent
        ) if (first_screen.parent / "analysis.json").exists() else None

        if analysis:
            generate_thumbnail(
                key_frames_dir=analysis.key_frames_dir,
                recommended_frame_index=analysis.recommended_thumbnail_frame,
                webcam_video=first_webcam,
                title_text=metadata.thumbnail_text,
                subtext=metadata.thumbnail_subtext,
                tone="energetic",
                output_path=thumbnail_path,
            )

        should_upload = preview_video(output_path)
        if not should_upload:
            return None

        yt_thumbnail = thumbnail_path if thumbnail_path.exists() else output_path
        return self._upload(output_path, yt_thumbnail, metadata)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _upload(self, video: Path, thumbnail: Path, metadata: VideoMetadata) -> Optional[str]:
        self._print_upload_summary(video, metadata)

        upload = questionary.confirm("Upload this video to YouTube now?", default=True).ask()
        if not upload:
            console.print(f"[yellow]Upload skipped.[/yellow] Video saved to: {video}")
            return None

        privacy = questionary.select(
            "Upload privacy:",
            choices=[
                questionary.Choice("Private   — only you", value="private"),
                questionary.Choice("Unlisted  — anyone with link", value="unlisted"),
                questionary.Choice("Public    — visible to everyone", value="public"),
            ],
        ).ask() or "private"

        title_idx = select_title_interactively(metadata)
        url = upload_to_youtube(video, thumbnail, metadata, title_idx, privacy)
        self._print_done(url, video, thumbnail)
        return url

    def _print_header(self, title: str) -> None:
        console.print()
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", title="YT AI Editor"))
        console.print()

    def _print_analysis_summary(self, analysis: AnalysisResult) -> None:
        top = analysis.top_moments(5)
        table = Table(title="Top Moments", show_header=True, header_style="bold cyan")
        table.add_column("Time", width=10)
        table.add_column("Score", width=7)
        table.add_column("Category", width=12)
        table.add_column("Description")
        for m in top:
            table.add_row(f"{m.timestamp_seconds:.0f}s", f"{m.highlight_score}/10",
                          m.category, m.description[:60])
        console.print(table)
        console.print(f"\n[dim]{analysis.session_summary}[/dim]\n")

    def _print_script_summary(self, script: VideoScript, metadata: VideoMetadata) -> None:
        console.print(Panel(
            "\n".join(f"  {i+1}. {t['title']}  [{t['style']}]"
                      for i, t in enumerate(metadata.titles)),
            title="[cyan]Generated Titles[/cyan]",
        ))
        chapters = script.chapters_text()
        if chapters:
            console.print(Panel(chapters, title="[cyan]Chapter Markers[/cyan]"))
        console.print(f"  Segments: {len(script.segments)}  |  "
                      f"Est. duration: {script.estimated_duration_seconds:.0f}s  |  "
                      f"Music mood: {script.dominant_mood}")
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _script_from_top_moments(analysis: AnalysisResult, target_minutes: int = 3) -> VideoScript:
    """Build a VideoScript directly from top-scored moments (quick clip / no-transcript path)."""
    from src.agents.scriptwriter import VideoScript, VideoSegment

    target_secs = target_minutes * 60
    top = sorted(analysis.moments, key=lambda m: m.highlight_score, reverse=True)
    top = [m for m in top if m.include_in_highlights][:15]
    # Sort by timestamp for chronological order
    top = sorted(top, key=lambda m: m.timestamp_seconds)

    clip_len = 20  # seconds per clip
    segments = []
    accumulated = 0.0
    for m in top:
        if accumulated >= target_secs:
            break
        start = max(0, m.timestamp_seconds - 3)
        end = m.timestamp_seconds + clip_len
        mood = {"peak": "energetic", "intense": "dramatic",
                "medium": "chill", "calm": "chill"}.get(m.energy, "energetic")
        segments.append(VideoSegment(
            name=m.description[:30],
            source_start=start,
            source_end=end,
            speed_multiplier=1.0,
            commentary="",
            music_mood=mood,
            include_webcam=True,
            caption=m.description[:50],
        ))
        accumulated += clip_len

    if not segments:
        segments = [VideoSegment(name="Highlights", source_start=0, source_end=180)]

    return VideoScript(
        title_options=["Gaming Highlights"],
        hook_script="",
        segments=segments,
        outro_script="",
        estimated_duration_seconds=accumulated,
    )


def _script_from_library_clips(clips: list) -> VideoScript:
    """Build a VideoScript from LibraryClip objects (best-of path)."""
    from src.agents.scriptwriter import VideoScript, VideoSegment

    segments = []
    for clip in clips[:20]:
        start = max(0, clip.timestamp_seconds - 3)
        end = clip.timestamp_seconds + 25
        segments.append(VideoSegment(
            name=clip.description[:30],
            source_start=start,
            source_end=end,
            music_mood="energetic" if clip.energy == "peak" else "chill",
            caption=clip.description[:50],
        ))

    return VideoScript(
        title_options=["Best Of Gaming"],
        hook_script="",
        segments=segments,
        outro_script="",
        estimated_duration_seconds=len(segments) * 25.0,
    )


def _quick_profile(game_name: str, tone: str) -> SessionProfile:
    from src.prompts.interview import SessionProfile
    return SessionProfile(
        game_name=game_name,
        channel_name="My Channel",
        video_type="highlights",
        audience="casual",
        tone=tone,
        target_length_minutes=3,
    )


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
