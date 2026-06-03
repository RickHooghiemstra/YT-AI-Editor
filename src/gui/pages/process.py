"""
Process page — interview form + live pipeline progress + title selection + upload.
This is the main action page.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Optional

from nicegui import ui

from src.gui.state import state, make_progress_callback


# ── Interview form defaults ───────────────────────────────────────────────────

VIDEO_TYPES = [
    ("highlights", "Highlights Reel  — best moments, 2–5 min"),
    ("commentary", "Full Commentary  — full session, 10–30 min"),
    ("tutorial",   "Tutorial / Guide — educational, tips-focused"),
    ("short",      "YouTube Short    — 60 seconds, vertical"),
]
AUDIENCES = [
    ("beginners", "Beginners — new to this game"),
    ("casual",    "Casual — plays occasionally"),
    ("hardcore",  "Hardcore — experienced players"),
]
TONES = [
    ("energetic",   "Energetic / Hype"),
    ("chill",       "Chill / Relaxed"),
    ("educational", "Educational"),
    ("funny",       "Funny / Meme-y"),
]


def process_page() -> None:
    # ── File source section ───────────────────────────────────────────
    with ui.column().classes("w-full gap-6"):

        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Source files").classes("text-h6 text-cyan")
            with ui.card_section().classes("flex flex-col gap-4"):

                # Auto-fill from last recording if available
                screen_input = ui.input("Screen recording path").classes("w-full")
                screen_input.props("outlined dense dark")
                webcam_input = ui.input("Webcam recording path").classes("w-full")
                webcam_input.props("outlined dense dark")
                audio_input = ui.input("Audio recording path").classes("w-full")
                audio_input.props("outlined dense dark")

                if state.last_session_dir:
                    d = state.last_session_dir
                    screen_input.value = str(d / "screen.mp4")
                    webcam_input.value = str(d / "webcam.mp4")
                    audio_input.value = str(d / "audio.wav")

                ui.label(
                    "Tip: record from the Record tab — paths fill automatically. "
                    "Or paste paths from OBS or any other recorder."
                ).classes("text-grey-6 text-caption")

        # ── Interview form ────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Video settings").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col gap-5"):
                game_input = ui.input("Game name", placeholder="Valorant") \
                    .classes("w-full")
                game_input.props("outlined dense dark")

                channel_input = ui.input("Your channel name", placeholder="RickPlays") \
                    .classes("w-full")
                channel_input.props("outlined dense dark")

                with ui.row().classes("w-full gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Video type").classes("text-subtitle2 text-grey-4")
                        video_type_sel = ui.select(
                            {k: v for k, v in VIDEO_TYPES},
                            value="highlights",
                        ).classes("w-full")
                        video_type_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Audience").classes("text-subtitle2 text-grey-4")
                        audience_sel = ui.select(
                            {k: v for k, v in AUDIENCES},
                            value="casual",
                        ).classes("w-full")
                        audience_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Tone").classes("text-subtitle2 text-grey-4")
                        tone_sel = ui.select(
                            {k: v for k, v in TONES},
                            value="energetic",
                        ).classes("w-full")
                        tone_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-32"):
                        ui.label("Target length (min)").classes("text-subtitle2 text-grey-4")
                        length_input = ui.number(value=4, min=1, max=60, step=1) \
                            .classes("w-full")
                        length_input.props("outlined dense dark")

                special_input = ui.textarea(
                    label="Specific moments to include (optional)",
                    placeholder="e.g. the clutch at minute 12, the funny death near the end",
                ).classes("w-full")
                special_input.props("outlined dark rows=2")

                extra_input = ui.textarea(
                    label="Anything else the AI should know (optional)",
                    placeholder="e.g. ranked match, Silver II, first time playing this map",
                ).classes("w-full")
                extra_input.props("outlined dark rows=2")

        # ── Start button ──────────────────────────────────────────────
        start_btn = ui.button("Start Processing", icon="play_arrow") \
            .classes("w-full text-h6 py-4 rounded-xl")
        start_btn.props("color=cyan size=lg")

        # ── Pipeline progress (hidden until started) ──────────────────
        progress_card = ui.card().classes("w-full bg-grey-10 rounded-2xl")
        progress_card.set_visibility(False)

        with progress_card:
            with ui.card_section():
                ui.label("Pipeline progress").classes("text-h6 text-cyan")
            with ui.card_section().classes("flex flex-col gap-3"):
                step_rows = _build_step_rows()

            log_expander = ui.expansion("Show log", icon="terminal").classes("w-full")
            with log_expander:
                log_area = ui.textarea().classes("w-full font-mono text-xs") \
                    .props("readonly outlined dark rows=8")

        # ── Results section ───────────────────────────────────────────
        results_card = ui.card().classes("w-full bg-grey-10 rounded-2xl")
        results_card.set_visibility(False)

        with results_card:
            with ui.card_section():
                ui.label("Pick a title").classes("text-h6 text-cyan")

            title_container = ui.card_section().classes("flex flex-col gap-3")

            with ui.card_section():
                privacy_sel = ui.select(
                    {"private": "Private — only you",
                     "unlisted": "Unlisted — anyone with the link",
                     "public": "Public — visible to everyone"},
                    value="private",
                    label="Upload privacy",
                ).classes("w-full")
                privacy_sel.props("outlined dense dark")

            upload_btn = ui.button("Upload to YouTube", icon="upload") \
                .classes("w-full py-3 rounded-xl")
            upload_btn.props("color=positive size=lg")

        # ── Wire up start button ──────────────────────────────────────
        def on_start():
            screen = Path(screen_input.value.strip())
            webcam = Path(webcam_input.value.strip())
            audio = Path(audio_input.value.strip())

            for f, name in [(screen, "Screen"), (webcam, "Webcam"), (audio, "Audio")]:
                if not f.exists():
                    ui.notify(f"{name} file not found: {f}", type="negative")
                    return
            if not game_input.value.strip():
                ui.notify("Please enter a game name", type="warning")
                return

            state.reset_pipeline()
            progress_card.set_visibility(True)
            results_card.set_visibility(False)
            start_btn.props("disable")
            start_btn.set_text("Processing…")

            profile_data = {
                "game_name": game_input.value.strip(),
                "channel_name": channel_input.value.strip() or "My Gaming Channel",
                "video_type": video_type_sel.value,
                "audience": audience_sel.value,
                "tone": tone_sel.value,
                "target_length_minutes": int(length_input.value or 4),
                "special_moments": special_input.value.strip(),
                "extra_context": extra_input.value.strip(),
            }

            def run():
                _run_pipeline(screen, webcam, audio, profile_data,
                              results_card, title_container, start_btn)

            threading.Thread(target=run, daemon=True).start()

        start_btn.on_click(on_start)

        # ── Live update timer ─────────────────────────────────────────
        def refresh_progress():
            for row in step_rows:
                key = row["key"]
                for s in state.steps:
                    if s.key == key:
                        row["icon"].props(f"color={s.color} name={s.icon}")
                        row["label"].set_text(s.label)
                        row["msg"].set_text(s.message)
                        row["bar"].set_value(s.progress / 100)
                        break
            # Update log
            log_area.value = "\n".join(state.log_lines[-50:])

        ui.timer(0.5, refresh_progress)

        # ── Wire up upload button ─────────────────────────────────────
        def on_upload():
            if not state.output_video or not state.output_video.exists():
                ui.notify("No video to upload", type="warning")
                return
            privacy = privacy_sel.value
            title_idx = state.selected_title_idx

            def do_upload():
                from src.modules.youtube_uploader import upload_to_youtube
                from src.agents.scriptwriter import VideoMetadata
                meta = VideoMetadata(
                    titles=state.generated_titles,
                    description="",
                    tags=[],
                    category_id="20",
                    thumbnail_text="",
                    thumbnail_subtext="",
                )
                url = upload_to_youtube(
                    state.output_video,
                    state.output_thumbnail or state.output_video,
                    meta,
                    title_idx,
                    privacy,
                )
                state.upload_url = url
                ui.notify(f"Uploaded! {url}", type="positive")

            threading.Thread(target=do_upload, daemon=True).start()

        upload_btn.on_click(on_upload)


def _build_step_rows() -> list[dict]:
    rows = []
    for s in state.steps:
        with ui.row().classes("w-full items-center gap-3"):
            icon = ui.icon(s.icon, size="1.5rem").props(f"color={s.color}")
            with ui.column().classes("flex-1"):
                lbl = ui.label(s.label).classes("text-subtitle2")
                msg = ui.label("").classes("text-caption text-grey-6")
                bar = ui.linear_progress(value=0, show_value=False) \
                    .props("color=cyan size=4px")
                bar.set_visibility(True)
        rows.append({"key": s.key, "icon": icon, "label": lbl, "msg": msg, "bar": bar})
    return rows


def _run_pipeline(
    screen: Path,
    webcam: Path,
    audio: Path,
    profile_data: dict,
    results_card,
    title_container,
    start_btn,
) -> None:
    from src.agents.orchestrator import Pipeline
    from src.prompts.interview import SessionProfile
    from src.utils.file_manager import session_id

    cb = make_progress_callback()

    profile = SessionProfile(
        game_name=profile_data["game_name"],
        channel_name=profile_data["channel_name"],
        video_type=profile_data["video_type"],
        audience=profile_data["audience"],
        tone=profile_data["tone"],
        target_length_minutes=profile_data["target_length_minutes"],
        special_moments=profile_data["special_moments"],
        extra_context=profile_data["extra_context"],
    )

    try:
        sid = session_id()
        pipeline = Pipeline(progress_callback=cb)
        result = pipeline.run_from_files(
            screen_file=screen,
            webcam_file=webcam,
            audio_file=audio,
            session_id=sid,
            profile_override=profile,
        )

        # Show results
        if result:
            state.output_video = result.get("video")
            state.output_thumbnail = result.get("thumbnail")
            state.generated_titles = result.get("titles", [])
            _populate_titles(title_container)
            results_card.set_visibility(True)
            ui.notify("Processing complete!", type="positive")
        else:
            ui.notify("Processing finished — no upload.", type="info")

    except Exception as e:
        state.pipeline_error = str(e)
        state.log(f"ERROR: {e}")
        ui.notify(f"Error: {e}", type="negative", timeout=0)

    finally:
        start_btn.props(remove="disable")
        start_btn.set_text("Start Processing")


def _populate_titles(container) -> None:
    container.clear()
    with container:
        for i, t in enumerate(state.generated_titles):
            def make_select(idx=i):
                def _select():
                    state.selected_title_idx = idx
                    ui.notify(f"Selected title {idx+1}", type="info")
                return _select

            with ui.card().classes("w-full cursor-pointer hover:bg-grey-9 rounded-xl") \
                    .on("click", make_select(i)):
                with ui.card_section().classes("flex items-start gap-3"):
                    ui.chip(str(i + 1), color="cyan").props("dense")
                    with ui.column():
                        ui.label(t.get("title", "")).classes("text-subtitle1")
                        ui.label(f"Style: {t.get('style', '')}").classes("text-caption text-grey-5")
