"""
Shared reactive state for the GUI.
All pages read from and write to this singleton.
NiceGUI's @ui.refreshable components observe it automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class PipelineStep:
    key: str
    label: str
    progress: float = 0.0      # 0–100
    status: str = "pending"    # pending | running | done | error
    message: str = ""

    @property
    def icon(self) -> str:
        return {"pending": "radio_button_unchecked",
                "running": "sync",
                "done": "check_circle",
                "error": "error"}[self.status]

    @property
    def color(self) -> str:
        return {"pending": "grey-6",
                "running": "cyan",
                "done": "positive",
                "error": "negative"}[self.status]


PIPELINE_STEPS = [
    ("transcribe", "Transcribe Audio"),
    ("analyze",    "Analyze Footage"),
    ("script",     "Generate Script"),
    ("avatar",     "Caricature Avatar"),
    ("edit",       "Edit Video"),
    ("music",      "Mix Music"),
    ("thumbnail",  "Generate Thumbnail"),
    ("metadata",   "Generate Metadata"),
    ("upload",     "Upload to YouTube"),
]


@dataclass
class AppState:
    # Recording
    is_recording: bool = False
    recording_seconds: float = 0.0
    quick_clip_mode: bool = False
    last_session_dir: Optional[Path] = None

    # Pipeline
    pipeline_running: bool = False
    pipeline_done: bool = False
    pipeline_error: Optional[str] = None
    steps: list[PipelineStep] = field(default_factory=lambda: [
        PipelineStep(k, l) for k, l in PIPELINE_STEPS
    ])
    log_lines: list[str] = field(default_factory=list)

    # Results
    generated_titles: list[dict] = field(default_factory=list)
    selected_title_idx: int = 0
    generated_description: str = ""
    generated_tags: list[str] = field(default_factory=list)
    output_video: Optional[Path] = None
    output_thumbnail: Optional[Path] = None
    upload_url: Optional[str] = None

    # Files (for manual process page)
    pending_screen: Optional[Path] = None
    pending_webcam: Optional[Path] = None
    pending_audio: Optional[Path] = None

    def reset_pipeline(self) -> None:
        self.pipeline_running = False
        self.pipeline_done = False
        self.pipeline_error = None
        self.steps = [PipelineStep(k, l) for k, l in PIPELINE_STEPS]
        self.log_lines = []
        self.generated_titles = []
        self.generated_description = ""
        self.generated_tags = []
        self.output_video = None
        self.output_thumbnail = None
        self.upload_url = None

    def step_start(self, key: str, message: str = "") -> None:
        for s in self.steps:
            if s.key == key:
                s.status = "running"
                s.progress = 0.0
                s.message = message

    def step_progress(self, key: str, pct: float, message: str = "") -> None:
        for s in self.steps:
            if s.key == key:
                s.progress = pct
                s.message = message

    def step_done(self, key: str, message: str = "") -> None:
        for s in self.steps:
            if s.key == key:
                s.status = "done"
                s.progress = 100.0
                s.message = message

    def step_error(self, key: str, message: str) -> None:
        for s in self.steps:
            if s.key == key:
                s.status = "error"
                s.message = message

    def log(self, message: str) -> None:
        self.log_lines.append(message)
        if len(self.log_lines) > 200:
            self.log_lines = self.log_lines[-200:]


# Singleton
state = AppState()


def make_progress_callback():
    """Returns a callback the pipeline calls to report progress to the GUI."""
    def callback(step_key: str, pct: float, message: str) -> None:
        if pct == 0:
            state.step_start(step_key, message)
        elif pct >= 100:
            state.step_done(step_key, message)
        else:
            state.step_progress(step_key, pct, message)
        state.log(f"[{step_key}] {message}")
    return callback
