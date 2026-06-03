"""
Record page — big record button, timer, quick-clip toggle.
Controls the hotkey recorder; also shows the last session status.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from nicegui import ui

from src.gui.state import state


def record_page() -> None:
    state.is_recording = False  # reset on page load

    with ui.column().classes("w-full items-center gap-6 py-10"):

        # ── Status card ──────────────────────────────────────────────
        with ui.card().classes("w-full max-w-2xl bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Recording").classes("text-h6 text-cyan")

            with ui.card_section().classes("flex flex-col items-center gap-6 py-6"):

                # Animated record indicator
                indicator = ui.icon("fiber_manual_record", size="4rem") \
                    .classes("text-grey-6")

                # Timer display
                timer_label = ui.label("00:00:00") \
                    .classes("text-h3 text-grey-4 font-mono")

                # Record / Stop button
                btn = ui.button("Start Recording", icon="videocam") \
                    .classes("text-h6 px-10 py-4 rounded-xl")
                btn.props("color=cyan size=lg")

                # Quick clip toggle
                with ui.row().classes("items-center gap-3 text-grey-5"):
                    quick_toggle = ui.switch("Quick Clip mode").props("color=cyan")
                    ui.tooltip(
                        "Skips transcription — 5 min instead of 20.\n"
                        "Best for fast posts; may miss audio-only highlights."
                    ).classes("max-w-xs")

            with ui.card_section():
                status_label = ui.label("Ready. Press the button or use Ctrl+Shift+R.") \
                    .classes("text-grey-5 text-sm")

        # ── Hotkey info ──────────────────────────────────────────────
        with ui.card().classes("w-full max-w-2xl bg-grey-10 rounded-2xl"):
            with ui.card_section():
                ui.label("Global hotkey").classes("text-subtitle1 text-grey-4")
            with ui.card_section().classes("flex items-center gap-4"):
                ui.chip("Ctrl+Shift+R", icon="keyboard").props("color=dark outline")
                ui.label("Works while any game is in focus — you never need to alt-tab.") \
                    .classes("text-grey-5 text-sm")

        # ── Recorder logic ───────────────────────────────────────────
        _recorder_ref = {"recorder": None, "thread": None, "start_time": 0.0}

        def toggle_recording():
            if not state.is_recording:
                _start_recording(_recorder_ref, btn, indicator, timer_label,
                                 status_label, quick_toggle, state)
            else:
                _stop_recording(_recorder_ref, btn, indicator, timer_label,
                                status_label, quick_toggle, state)

        btn.on_click(toggle_recording)

        # Timer update loop
        def tick():
            if state.is_recording:
                elapsed = time.time() - _recorder_ref["start_time"]
                h = int(elapsed // 3600)
                m = int((elapsed % 3600) // 60)
                s = int(elapsed % 60)
                timer_label.set_text(f"{h:02d}:{m:02d}:{s:02d}")

        ui.timer(1.0, tick)


def _start_recording(ref, btn, indicator, timer_label, status_label, quick_toggle, state):
    from src.modules.recorder import Recorder
    recorder = Recorder()
    session = recorder.start()
    ref["recorder"] = recorder
    ref["start_time"] = time.time()
    state.is_recording = True
    state.quick_clip_mode = quick_toggle.value
    state.last_session_dir = session.session_dir

    btn.set_text("Stop Recording")
    btn.props("color=negative")
    indicator.classes("text-negative animate-pulse", remove="text-grey-6")
    timer_label.classes("text-negative", remove="text-grey-4")
    status_label.set_text("Recording in progress — play your game. Press Stop when done.")
    quick_toggle.props("disable")


def _stop_recording(ref, btn, indicator, timer_label, status_label, quick_toggle, state):
    recorder = ref.get("recorder")
    if recorder:
        session = recorder.stop()
        state.is_recording = False
        ref["recorder"] = None

        btn.set_text("Start Recording")
        btn.props("color=cyan")
        indicator.classes("text-grey-6", remove="text-negative animate-pulse")
        timer_label.classes("text-grey-4", remove="text-negative")
        quick_toggle.props(remove="disable")

        duration = session.duration_seconds
        m, s = int(duration // 60), int(duration % 60)
        status_label.set_text(f"Captured {m}m {s}s. Head to Process to build your video.")

        ui.notify(
            f"Recording saved — {m}m {s}s. Go to Process →",
            type="positive",
            position="top-right",
        )
