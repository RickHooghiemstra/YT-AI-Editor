"""
Settings page — API keys, recording devices, avatar, Whisper model.
Reads/writes the .env file directly.
"""

from __future__ import annotations

from pathlib import Path

from nicegui import ui


ENV_PATH = Path(".env")


def settings_page() -> None:
    current = _load_env()

    with ui.column().classes("w-full gap-6"):

        # ── API Keys ──────────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("API Keys").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col gap-4"):
                anthropic_input = ui.input(
                    "Anthropic API Key",
                    placeholder="sk-ant-...",
                    value=current.get("ANTHROPIC_API_KEY", ""),
                ).classes("w-full")
                anthropic_input.props("outlined dense dark password")
                ui.link("Get a key → console.anthropic.com",
                        "https://console.anthropic.com", new_tab=True) \
                    .classes("text-cyan text-caption")

        # ── Recording ─────────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Recording").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-wrap gap-4"):
                resolution_input = ui.input(
                    "Screen resolution",
                    placeholder="1920x1080",
                    value=current.get("SCREEN_RESOLUTION", "1920x1080"),
                ).classes("flex-1 min-w-40")
                resolution_input.props("outlined dense dark")

                fps_input = ui.number(
                    "FPS", value=int(current.get("SCREEN_FPS", "30")),
                    min=15, max=60,
                ).classes("flex-1 min-w-28")
                fps_input.props("outlined dense dark")

                webcam_input = ui.input(
                    "Webcam device",
                    placeholder="/dev/video0  or  0  (Windows index)",
                    value=current.get("WEBCAM_DEVICE", "/dev/video0"),
                ).classes("flex-1 min-w-48")
                webcam_input.props("outlined dense dark")

                audio_input = ui.input(
                    "Audio device",
                    placeholder="default",
                    value=current.get("AUDIO_DEVICE", "default"),
                ).classes("flex-1 min-w-48")
                audio_input.props("outlined dense dark")

        # ── Avatar ────────────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Caricature avatar").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col gap-4"):
                with ui.row().classes("w-full items-center gap-6"):
                    with ui.column().classes("flex-1"):
                        ui.label("Exaggeration").classes("text-subtitle2 text-grey-4")
                        exag_slider = ui.slider(min=1.0, max=4.0, step=0.1,
                                                value=2.5).classes("w-full")
                        exag_label = ui.label("2.5×").classes("text-caption text-grey-5")
                        exag_slider.on("update:model-value",
                                       lambda e: exag_label.set_text(f"{e.args:.1f}×"))

                    with ui.column().classes("flex-1"):
                        ui.label("Cartoon strength").classes("text-subtitle2 text-grey-4")
                        cartoon_slider = ui.slider(min=0.0, max=1.0, step=0.05,
                                                   value=0.75).classes("w-full")
                        cartoon_label = ui.label("75%").classes("text-caption text-grey-5")
                        cartoon_slider.on("update:model-value",
                                          lambda e: cartoon_label.set_text(f"{e.args*100:.0f}%"))

                ui.label(
                    "Tip: use avatar-preview from CLI to see changes live — "
                    "python main.py avatar-preview --exaggeration 2.5"
                ).classes("text-grey-6 text-caption")

        # ── Whisper model ─────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Whisper transcription").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col gap-4"):
                whisper_sel = ui.select(
                    {
                        "tiny":     "tiny   — fast, 1 GB GPU, good accuracy",
                        "base":     "base   — fast, 1 GB GPU, better accuracy  (default)",
                        "small":    "small  — medium speed, 2 GB GPU, great",
                        "medium":   "medium — slower, 5 GB GPU, excellent",
                        "large-v3": "large-v3 — best accuracy, 10 GB GPU",
                    },
                    value=current.get("WHISPER_MODEL", "base"),
                    label="Model size",
                ).classes("w-full")
                whisper_sel.props("outlined dark")
                ui.label("Downloads automatically on first use.") \
                    .classes("text-grey-6 text-caption")

        # ── YouTube ───────────────────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("YouTube").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col gap-3"):
                secrets_path = current.get("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
                exists = Path(secrets_path).exists()
                icon = "check_circle" if exists else "error"
                color = "positive" if exists else "warning"
                with ui.row().classes("items-center gap-3"):
                    ui.icon(icon, color=color)
                    label_text = (
                        f"client_secrets.json found ({secrets_path})"
                        if exists
                        else "client_secrets.json not found — follow the setup guide below"
                    )
                    ui.label(label_text).classes("text-sm")

                with ui.expansion("YouTube setup guide", icon="help").classes("w-full"):
                    ui.markdown("""
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → New Project
2. **APIs & Services → Library** → search YouTube Data API v3 → Enable
3. **Credentials → + Create → OAuth client ID**
4. Consent screen: External, add your Gmail as test user, scope `youtube.upload`
5. Application type: Desktop app → Create → Download JSON
6. Save the file as `client_secrets.json` in the project folder

First upload opens a browser tab for approval. After that, fully automatic.
                    """).classes("text-grey-4 text-sm")

        # ── Channel / social links ────────────────────────────────────
        with ui.card().classes("w-full bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Channel & social links").classes("text-h6 text-cyan")
            with ui.card_section().classes("flex flex-col gap-4"):
                ui.label(
                    "Appended to every generated video description automatically."
                ).classes("text-grey-6 text-caption")

                with ui.row().classes("w-full gap-4 flex-wrap"):
                    twitter_input = ui.input(
                        "Twitter / X", placeholder="https://twitter.com/yourchannel",
                        value=current.get("CHANNEL_TWITTER", ""),
                    ).classes("flex-1 min-w-48")
                    twitter_input.props("outlined dense dark")

                    twitch_input = ui.input(
                        "Twitch", placeholder="https://twitch.tv/yourchannel",
                        value=current.get("CHANNEL_TWITCH", ""),
                    ).classes("flex-1 min-w-48")
                    twitch_input.props("outlined dense dark")

                    instagram_input = ui.input(
                        "Instagram", placeholder="https://instagram.com/yourchannel",
                        value=current.get("CHANNEL_INSTAGRAM", ""),
                    ).classes("flex-1 min-w-48")
                    instagram_input.props("outlined dense dark")

                    tiktok_input = ui.input(
                        "TikTok", placeholder="https://tiktok.com/@yourchannel",
                        value=current.get("CHANNEL_TIKTOK", ""),
                    ).classes("flex-1 min-w-48")
                    tiktok_input.props("outlined dense dark")

                footer_input = ui.textarea(
                    label="Custom description footer (optional)",
                    placeholder="e.g. Business enquiries: email@example.com",
                    value=current.get("CHANNEL_DESCRIPTION_FOOTER", ""),
                ).classes("w-full")
                footer_input.props("outlined dark rows=2")

        # ── Save button ───────────────────────────────────────────────
        def save():
            updates = {
                "ANTHROPIC_API_KEY":          anthropic_input.value.strip(),
                "SCREEN_RESOLUTION":          resolution_input.value.strip(),
                "SCREEN_FPS":                 str(int(fps_input.value or 30)),
                "WEBCAM_DEVICE":              webcam_input.value.strip(),
                "AUDIO_DEVICE":              audio_input.value.strip(),
                "WHISPER_MODEL":              whisper_sel.value,
                "CHANNEL_TWITTER":            twitter_input.value.strip(),
                "CHANNEL_TWITCH":             twitch_input.value.strip(),
                "CHANNEL_INSTAGRAM":          instagram_input.value.strip(),
                "CHANNEL_TIKTOK":             tiktok_input.value.strip(),
                "CHANNEL_DESCRIPTION_FOOTER": footer_input.value.strip(),
            }
            _save_env(updates)
            ui.notify("Settings saved — restart the app to apply changes.", type="positive")

        ui.button("Save Settings", icon="save", on_click=save) \
            .props("color=cyan size=lg") \
            .classes("w-full py-3 rounded-xl")


def _load_env() -> dict[str, str]:
    result = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _save_env(updates: dict[str, str]) -> None:
    existing = {}
    lines = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, v = stripped.partition("=")
                existing[k.strip()] = len(lines)
            lines.append(line)

    for key, value in updates.items():
        if key in existing:
            lines[existing[key]] = f"{key}={value}"
        else:
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n")
