"""
Manages FFmpeg-based concurrent recording of screen, webcam, and audio.
Triggered by global hotkey (pynput). Works on Linux (X11/Wayland) and macOS.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from src.utils.config import get_settings
from src.utils.file_manager import get_session_dir, session_id

console = Console()


@dataclass
class RecordingSession:
    session_id: str
    session_dir: Path
    screen_file: Path
    webcam_file: Path
    audio_file: Path
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def all_files_exist(self) -> bool:
        return (
            self.screen_file.exists()
            and self.webcam_file.exists()
            and self.audio_file.exists()
        )


class Recorder:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._procs: list[subprocess.Popen] = []
        self._session: Optional[RecordingSession] = None
        self._recording = False
        self._lock = threading.Lock()

    def start(self) -> RecordingSession:
        with self._lock:
            if self._recording:
                raise RuntimeError("Already recording")

            sid = session_id()
            session_dir = get_session_dir(self.settings.raw_recordings_dir, sid)

            screen_file = session_dir / "screen.mp4"
            webcam_file = session_dir / "webcam.mp4"
            audio_file = session_dir / "audio.wav"

            self._session = RecordingSession(
                session_id=sid,
                session_dir=session_dir,
                screen_file=screen_file,
                webcam_file=webcam_file,
                audio_file=audio_file,
            )

            self._procs = [
                self._start_screen_recording(screen_file),
                self._start_webcam_recording(webcam_file),
                self._start_audio_recording(audio_file),
            ]
            self._recording = True
            console.print(f"[green]Recording started[/green] — session [cyan]{sid}[/cyan]")
            console.print("[dim]Press Ctrl+Shift+R again to stop[/dim]")
            return self._session

    def stop(self) -> RecordingSession:
        with self._lock:
            if not self._recording or self._session is None:
                raise RuntimeError("Not recording")

            for proc in self._procs:
                try:
                    proc.send_signal(signal.SIGINT)
                except ProcessLookupError:
                    pass

            for proc in self._procs:
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

            self._session.end_time = time.time()
            self._recording = False
            self._procs = []

            duration = self._session.duration_seconds
            mins, secs = int(duration // 60), int(duration % 60)
            console.print(f"[green]Recording stopped[/green] — {mins}m {secs}s captured")
            return self._session

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _start_screen_recording(self, output: Path) -> subprocess.Popen:
        w, h = self.settings.screen_width, self.settings.screen_height
        fps = self.settings.screen_fps
        cmd = self._screen_cmd(w, h, fps, output)
        return subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _start_webcam_recording(self, output: Path) -> subprocess.Popen:
        cmd = self._webcam_cmd(output)
        return subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _start_audio_recording(self, output: Path) -> subprocess.Popen:
        cmd = self._audio_cmd(output)
        return subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _screen_cmd(self, w: int, h: int, fps: int, output: Path) -> list[str]:
        if sys.platform == "linux":
            display = ":0.0"
            return [
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-r", str(fps),
                "-s", f"{w}x{h}",
                "-i", f"{display}+0,0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                str(output),
            ]
        elif sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", str(fps),
                "-i", "1",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                str(output),
            ]
        else:
            return [
                "ffmpeg", "-y",
                "-f", "gdigrab",
                "-framerate", str(fps),
                "-i", "desktop",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                str(output),
            ]

    def _webcam_cmd(self, output: Path) -> list[str]:
        device = self.settings.webcam_device
        if sys.platform == "linux":
            return [
                "ffmpeg", "-y",
                "-f", "v4l2",
                "-r", "30",
                "-i", device,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                str(output),
            ]
        elif sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", "30",
                "-i", "0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                str(output),
            ]
        else:
            return [
                "ffmpeg", "-y",
                "-f", "dshow",
                "-i", "video=Integrated Camera",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                str(output),
            ]

    def _audio_cmd(self, output: Path) -> list[str]:
        if sys.platform == "linux":
            return [
                "ffmpeg", "-y",
                "-f", "pulse",
                "-i", self.settings.audio_device,
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                str(output),
            ]
        elif sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-i", ":0",
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                str(output),
            ]
        else:
            return [
                "ffmpeg", "-y",
                "-f", "dshow",
                "-i", "audio=Microphone",
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                str(output),
            ]


def run_hotkey_daemon(hotkey: str = "<ctrl>+<shift>+r") -> None:
    """
    Background daemon: listens for the hotkey globally.
    Starts recording on first press, stops on second press.
    Exits cleanly with Ctrl+C.
    """
    try:
        from pynput import keyboard
    except ImportError:
        console.print("[red]pynput not installed. Run: pip install pynput[/red]")
        return

    recorder = Recorder()
    combo = _parse_hotkey(hotkey)

    currently_pressed: set = set()

    def on_press(key):
        currently_pressed.add(key)
        if _matches(currently_pressed, combo):
            if recorder.is_recording:
                try:
                    recorder.stop()
                except Exception as e:
                    console.print(f"[red]Stop error: {e}[/red]")
            else:
                try:
                    recorder.start()
                except Exception as e:
                    console.print(f"[red]Start error: {e}[/red]")

    def on_release(key):
        currently_pressed.discard(key)

    console.print(Panel(
        f"[cyan]Hotkey recorder ready[/cyan]\n\n"
        f"Press [bold]{hotkey}[/bold] to start/stop recording.\n"
        f"Press [bold]Ctrl+C[/bold] to quit.",
        title="YT AI Editor",
    ))

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            if recorder.is_recording:
                recorder.stop()
            console.print("[yellow]Recorder stopped.[/yellow]")


def _parse_hotkey(hotkey: str) -> list:
    """Parse '<ctrl>+<shift>+r' into a list of pynput key objects."""
    from pynput import keyboard

    mapping = {
        "<ctrl>": keyboard.Key.ctrl,
        "<shift>": keyboard.Key.shift,
        "<alt>": keyboard.Key.alt,
        "<cmd>": keyboard.Key.cmd,
    }
    parts = hotkey.lower().split("+")
    result = []
    for p in parts:
        p = p.strip()
        if p in mapping:
            result.append(mapping[p])
        else:
            result.append(keyboard.KeyCode.from_char(p))
    return result


def _matches(pressed: set, combo: list) -> bool:
    from pynput import keyboard

    for key in combo:
        if isinstance(key, keyboard.Key):
            # Check modifier variants
            if key == keyboard.Key.ctrl:
                if keyboard.Key.ctrl not in pressed and keyboard.Key.ctrl_l not in pressed and keyboard.Key.ctrl_r not in pressed:
                    return False
            elif key == keyboard.Key.shift:
                if keyboard.Key.shift not in pressed and keyboard.Key.shift_l not in pressed and keyboard.Key.shift_r not in pressed:
                    return False
            elif key == keyboard.Key.alt:
                if keyboard.Key.alt not in pressed and keyboard.Key.alt_l not in pressed and keyboard.Key.alt_r not in pressed:
                    return False
            elif key not in pressed:
                return False
        elif key not in pressed:
            return False
    return True
