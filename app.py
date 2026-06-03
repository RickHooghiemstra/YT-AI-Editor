#!/usr/bin/env python3
"""
YT AI Editor — Browser-based desktop GUI.
Opens automatically in your default browser at localhost:8080.
"""

from __future__ import annotations

import threading
import webbrowser
import time
from pathlib import Path

from nicegui import app, ui

from src.gui.pages.record import record_page
from src.gui.pages.process import process_page
from src.gui.pages.library import library_page
from src.gui.pages.settings import settings_page


# ── Theme & colours ───────────────────────────────────────────────────────────
ui.colors(
    primary="#00d4aa",       # cyan-teal accent
    secondary="#1a1a2e",     # dark navy
    accent="#ff4757",        # red (recording indicator)
    dark="#0f0f1a",          # near-black background
    positive="#23d160",
    negative="#ff4757",
    warning="#ffb300",
)

NAV_ITEMS = [
    ("record",   "videocam",      "Record"),
    ("process",  "auto_fix_high", "Process"),
    ("library",  "video_library", "Clip Library"),
    ("settings", "settings",      "Settings"),
]


def _sidebar(current_tab: str) -> None:
    with ui.left_drawer(fixed=True).classes("bg-grey-10 flex flex-col") \
            .style("width:200px; padding-top:16px"):

        # Logo
        with ui.column().classes("items-center px-4 pb-6"):
            ui.icon("sports_esports", size="2.5rem").classes("text-cyan")
            ui.label("YT AI Editor").classes("text-subtitle1 text-cyan font-bold")

        ui.separator().classes("bg-grey-8 mb-4")

        # Nav links
        for key, icon, label in NAV_ITEMS:
            active = key == current_tab
            bg = "bg-grey-9" if active else ""
            text_col = "text-cyan" if active else "text-grey-4"
            with ui.row().classes(f"items-center gap-3 px-4 py-3 rounded-lg cursor-pointer w-full {bg}") \
                    .on("click", lambda k=key: ui.navigate.to(f"/{k}")):
                ui.icon(icon, size="1.4rem").classes(text_col)
                ui.label(label).classes(f"text-subtitle2 {text_col}")

        # Version at bottom
        ui.space()
        with ui.column().classes("items-center pb-4"):
            ui.label("v1.0.0").classes("text-caption text-grey-8")


def _header(title: str) -> None:
    with ui.header().classes("bg-grey-10 border-b border-grey-9 px-6 py-3") \
            .style("min-height:56px"):
        with ui.row().classes("items-center gap-4"):
            ui.label(title).classes("text-h6 text-grey-3")


@ui.page("/")
@ui.page("/record")
def page_record():
    ui.dark_mode(True)
    _header("Record")
    _sidebar("record")
    with ui.page_sticky(position="top-left").classes("ml-52 mt-14"):
        pass
    with ui.column().classes("ml-52 mt-14 p-6 w-full"):
        record_page()


@ui.page("/process")
def page_process():
    ui.dark_mode(True)
    _header("Process")
    _sidebar("process")
    with ui.column().classes("ml-52 mt-14 p-6 w-full"):
        process_page()


@ui.page("/library")
def page_library():
    ui.dark_mode(True)
    _header("Clip Library")
    _sidebar("library")
    with ui.column().classes("ml-52 mt-14 p-6 w-full"):
        library_page()


@ui.page("/settings")
def page_settings():
    ui.dark_mode(True)
    _header("Settings")
    _sidebar("settings")
    with ui.column().classes("ml-52 mt-14 p-6 w-full"):
        settings_page()


def _open_browser() -> None:
    """Open browser after NiceGUI has started."""
    time.sleep(1.2)
    webbrowser.open("http://localhost:8080")


if __name__ in {"__main__", "__mp_main__"}:
    from src.utils.config import get_settings
    get_settings().ensure_dirs()

    threading.Thread(target=_open_browser, daemon=True).start()

    ui.run(
        host="localhost",
        port=8080,
        title="YT AI Editor",
        favicon="🎮",
        dark=True,
        reload=False,
        show=False,       # we open the browser ourselves
    )
