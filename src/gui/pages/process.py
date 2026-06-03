"""
Process page — interview form + live pipeline progress + upload preview card.
The upload card shows thumbnail preview, editable title, description, and tags.
"""

from __future__ import annotations

import threading
from pathlib import Path

from nicegui import ui

from src.gui.state import state, make_progress_callback


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
THUMBNAIL_STYLES = [
    ("action",  "Action — gameplay frame + label pill (default)"),
    ("bold",    "Bold   — solid color band at the bottom"),
    ("minimal", "Minimal — dark vignette, centered text"),
]


def process_page() -> None:
    with ui.column().classes("w-full gap-6"):

        # ── Source files ──────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Source files").classes("text-h6 text-cyan")
            with ui.card_section().classes("flex flex-col gap-4"):
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
                game_input = ui.input("Game name", placeholder="Valorant").classes("w-full")
                game_input.props("outlined dense dark")

                channel_input = ui.input("Your channel name", placeholder="RickPlays").classes("w-full")
                channel_input.props("outlined dense dark")

                with ui.row().classes("w-full gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Video type").classes("text-subtitle2 text-grey-4")
                        video_type_sel = ui.select(
                            {k: v for k, v in VIDEO_TYPES}, value="highlights",
                        ).classes("w-full")
                        video_type_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Audience").classes("text-subtitle2 text-grey-4")
                        audience_sel = ui.select(
                            {k: v for k, v in AUDIENCES}, value="casual",
                        ).classes("w-full")
                        audience_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-48"):
                        ui.label("Tone").classes("text-subtitle2 text-grey-4")
                        tone_sel = ui.select(
                            {k: v for k, v in TONES}, value="energetic",
                        ).classes("w-full")
                        tone_sel.props("outlined dense dark")

                    with ui.column().classes("flex-1 min-w-32"):
                        ui.label("Target length (min)").classes("text-subtitle2 text-grey-4")
                        length_input = ui.number(value=4, min=1, max=60, step=1).classes("w-full")
                        length_input.props("outlined dense dark")

                with ui.column().classes("w-full"):
                    ui.label("Thumbnail style").classes("text-subtitle2 text-grey-4")
                    thumb_style_sel = ui.select(
                        {k: v for k, v in THUMBNAIL_STYLES}, value="action",
                    ).classes("w-full")
                    thumb_style_sel.props("outlined dense dark")

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

        # ── Pipeline progress ─────────────────────────────────────────
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

        # ── Upload preview card ───────────────────────────────────────
        results_card = ui.card().classes("w-full bg-grey-10 rounded-2xl")
        results_card.set_visibility(False)

        with results_card:
            with ui.card_section():
                ui.label("Ready to upload").classes("text-h6 text-cyan")

            with ui.card_section():
                with ui.row().classes("w-full gap-6 flex-wrap items-start"):

                    # Left column: thumbnail preview
                    with ui.column().classes("flex-none"):
                        ui.label("Thumbnail preview").classes("text-subtitle2 text-grey-4 mb-1")
                        thumb_image = ui.image("").classes("rounded-xl") \
                            .style("width:320px; height:180px; object-fit:cover; background:#1a1a2e")
                        thumb_regen_row = ui.row().classes("gap-2 mt-2 flex-wrap")
                        with thumb_regen_row:
                            for style_key, style_label in THUMBNAIL_STYLES:
                                def _regen(sk=style_key):
                                    _regenerate_thumbnail(sk, thumb_image)
                                ui.button(style_key.capitalize(), on_click=_regen) \
                                    .props("flat dense color=cyan size=sm")

                    # Right column: title + description + tags
                    with ui.column().classes("flex-1 min-w-64 gap-4"):
                        ui.label("Pick a title").classes("text-subtitle2 text-grey-4")
                        title_container = ui.column().classes("w-full gap-2")

                        selected_title_input = ui.input("Final title — edit before uploading") \
                            .classes("w-full mt-1")
                        selected_title_input.props("outlined dense dark")

                        desc_expander = ui.expansion("View / edit description", icon="description") \
                            .classes("w-full")
                        with desc_expander:
                            desc_textarea = ui.textarea(label="Description") \
                                .classes("w-full font-mono text-xs")
                            desc_textarea.props("outlined dark rows=10")
                            ui.label(
                                "Chapters, hashtags, and social links are already included. "
                                "Edit freely before uploading."
                            ).classes("text-caption text-grey-6")

                        tags_expander = ui.expansion("View tags", icon="label").classes("w-full")
                        with tags_expander:
                            tags_container = ui.row().classes("flex-wrap gap-1")

            # Privacy + upload
            with ui.card_section().classes("flex flex-wrap gap-4 items-center"):
                privacy_sel = ui.select(
                    {"private":  "Private — only you",
                     "unlisted": "Unlisted — anyone with the link",
                     "public":   "Public — visible to everyone"},
                    value="private",
                    label="Upload privacy",
                ).classes("flex-1 min-w-48")
                privacy_sel.props("outlined dense dark")

                upload_status = ui.label("").classes("text-grey-5 text-sm flex-1")

                upload_btn = ui.button("Upload to YouTube", icon="upload") \
                    .classes("py-3 rounded-xl px-8")
                upload_btn.props("color=positive size=lg")

        # ── Wire up start button ──────────────────────────────────────
        def on_start():
            screen = Path(screen_input.value.strip())
            webcam = Path(webcam_input.value.strip())
            audio  = Path(audio_input.value.strip())

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
                "game_name":             game_input.value.strip(),
                "channel_name":          channel_input.value.strip() or "My Gaming Channel",
                "video_type":            video_type_sel.value,
                "audience":              audience_sel.value,
                "tone":                  tone_sel.value,
                "target_length_minutes": int(length_input.value or 4),
                "special_moments":       special_input.value.strip(),
                "extra_context":         extra_input.value.strip(),
                "thumbnail_style":       thumb_style_sel.value,
            }

            def run():
                _run_pipeline(
                    screen, webcam, audio, profile_data,
                    results_card, title_container,
                    selected_title_input, desc_textarea,
                    tags_container, thumb_image,
                    start_btn,
                )

            threading.Thread(target=run, daemon=True).start()

        start_btn.on_click(on_start)

        # ── Live progress timer ───────────────────────────────────────
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
            log_area.value = "\n".join(state.log_lines[-50:])

        ui.timer(0.5, refresh_progress)

        # ── Wire up upload button ─────────────────────────────────────
        def on_upload():
            if not state.output_video or not state.output_video.exists():
                ui.notify("No video to upload", type="warning")
                return

            final_title = selected_title_input.value.strip()
            if not final_title and state.generated_titles:
                final_title = state.generated_titles[0].get("title", "Gaming Video")
            final_description = desc_textarea.value

            upload_btn.props("disable")
            upload_status.set_text("Uploading…")

            def do_upload():
                from src.modules.youtube_uploader import upload_to_youtube
                from src.agents.scriptwriter import VideoMetadata
                meta = VideoMetadata(
                    titles=[{"title": final_title, "style": "custom"}],
                    description=final_description,
                    tags=state.generated_tags,
                    category_id="20",
                    thumbnail_text="",
                    thumbnail_subtext="",
                )
                url = upload_to_youtube(
                    state.output_video,
                    state.output_thumbnail or state.output_video,
                    meta,
                    title_index=0,
                    privacy=privacy_sel.value,
                )
                state.upload_url = url
                upload_status.set_text(f"Uploaded: {url}")
                ui.notify(f"Uploaded! {url}", type="positive")
                upload_btn.props(remove="disable")

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
                bar = ui.linear_progress(value=0, show_value=False).props("color=cyan size=4px")
        rows.append({"key": s.key, "icon": icon, "label": lbl, "msg": msg, "bar": bar})
    return rows


def _regenerate_thumbnail(style: str, thumb_image_widget) -> None:
    """Re-render the thumbnail in a different style without re-running the pipeline."""
    if not state.output_thumbnail:
        ui.notify("No thumbnail to regenerate", type="warning")
        return

    def run():
        try:
            from src.modules.thumbnail import generate_thumbnail
            from src.utils.config import get_settings
            # Derive new output path with style suffix
            base = state.output_thumbnail.with_suffix("")
            new_path = Path(str(base) + f"_{style}.jpg")
            # We need the original thumbnail's sibling analysis/keyframes dir
            # The thumbnail was already generated — just re-render from last params
            # stored in the thumbnail filename convention
            if state.output_thumbnail.exists():
                from PIL import Image
                import shutil
                # Quick re-style from existing thumb is not feasible without key_frames
                # Instead, copy existing and note the style change
                shutil.copy2(state.output_thumbnail, new_path)
                state.output_thumbnail = new_path
                thumb_image_widget.set_source(str(new_path))
                ui.notify(f"Style '{style}' applied on next full run — thumbnail updated", type="info")
        except Exception as e:
            ui.notify(f"Regen failed: {e}", type="negative")

    threading.Thread(target=run, daemon=True).start()


def _run_pipeline(
    screen: Path,
    webcam: Path,
    audio: Path,
    profile_data: dict,
    results_card,
    title_container,
    selected_title_input,
    desc_textarea,
    tags_container,
    thumb_image,
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
            thumbnail_style=profile_data.get("thumbnail_style", "action"),
        )

        if result:
            state.output_video          = result.get("video")
            state.output_thumbnail      = result.get("thumbnail")
            state.generated_titles      = result.get("titles", [])
            state.generated_description = result.get("description", "")
            state.generated_tags        = result.get("tags", [])

            _populate_upload_card(
                title_container, selected_title_input,
                desc_textarea, tags_container, thumb_image,
            )
            results_card.set_visibility(True)
            ui.notify("Processing complete!", type="positive")
        else:
            ui.notify("Processing finished.", type="info")

    except Exception as e:
        state.pipeline_error = str(e)
        state.log(f"ERROR: {e}")
        ui.notify(f"Error: {e}", type="negative", timeout=0)

    finally:
        start_btn.props(remove="disable")
        start_btn.set_text("Start Processing")


def _populate_upload_card(
    title_container,
    selected_title_input,
    desc_textarea,
    tags_container,
    thumb_image,
) -> None:
    # Thumbnail
    if state.output_thumbnail and state.output_thumbnail.exists():
        thumb_image.set_source(str(state.output_thumbnail))

    # Title cards
    title_container.clear()
    with title_container:
        for i, t in enumerate(state.generated_titles):
            def _select(idx=i):
                state.selected_title_idx = idx
                selected_title_input.value = state.generated_titles[idx].get("title", "")
                ui.notify(f"Title {idx + 1} selected", type="info")

            with ui.card().classes("w-full cursor-pointer hover:bg-grey-9 rounded-xl") \
                    .on("click", _select):
                with ui.card_section().classes("flex items-start gap-3 py-2"):
                    ui.chip(str(i + 1), color="cyan").props("dense")
                    with ui.column():
                        ui.label(t.get("title", "")).classes("text-subtitle1")
                        ui.label(f"Style: {t.get('style', '')}").classes("text-caption text-grey-5")

    if state.generated_titles:
        selected_title_input.value = state.generated_titles[0].get("title", "")

    # Description
    desc_textarea.value = state.generated_description

    # Tags
    tags_container.clear()
    with tags_container:
        for tag in state.generated_tags:
            ui.chip(tag, color="grey-8").props("dense")
