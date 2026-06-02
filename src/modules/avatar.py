"""
Avatar processor: applies the caricature filter to a recorded webcam video.
Two modes:
  - calibrate(photo_path) — learn your neutral face from one photo
  - process_video(input, output) — render the caricature version of a recording
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

from src.modules.caricature import CaricatureFilter, NeutralBaseline

console = Console()

BASELINE_FILENAME = "neutral_baseline.json"


class AvatarProcessor:
    def __init__(
        self,
        exaggeration: float = 2.5,
        cartoon_strength: float = 0.75,
        baseline_dir: Optional[Path] = None,
    ) -> None:
        self.exaggeration = exaggeration
        self.cartoon_strength = cartoon_strength
        self.baseline_dir = baseline_dir or Path(".")
        self._filter: Optional[CaricatureFilter] = None

    def _get_filter(self) -> CaricatureFilter:
        if self._filter is None:
            neutral = self._load_baseline()
            self._filter = CaricatureFilter(
                exaggeration=self.exaggeration,
                cartoon_strength=self.cartoon_strength,
                neutral=neutral,
            )
        return self._filter

    def calibrate_from_photo(self, photo_path: Path) -> NeutralBaseline:
        """
        Read a photo of the user, detect their neutral face landmarks,
        and save as the personal baseline for all future processing.
        """
        console.print(f"[cyan]Calibrating from photo:[/cyan] {photo_path.name}")

        frame = cv2.imread(str(photo_path))
        if frame is None:
            raise FileNotFoundError(f"Cannot read photo: {photo_path}")

        filt = CaricatureFilter(exaggeration=1.0)
        baseline = filt.calibrate(frame)
        filt.close()

        baseline_path = self.baseline_dir / BASELINE_FILENAME
        baseline.save(baseline_path)

        console.print(f"[green]Baseline saved:[/green] {baseline_path}")
        console.print(f"  mouth_open_ratio:    {baseline.mouth_open_ratio:.4f}")
        console.print(f"  smile_ratio:         {baseline.smile_ratio:.4f}")
        console.print(f"  left_eye_ratio:      {baseline.left_eye_ratio:.4f}")
        console.print(f"  left_brow_eye_ratio: {baseline.left_brow_eye_ratio:.4f}")

        # Reset filter so it reloads with new baseline
        if self._filter:
            self._filter.close()
            self._filter = None

        return baseline

    def process_video(
        self,
        input_path: Path,
        output_path: Path,
        preview: bool = False,
    ) -> Path:
        """
        Render caricature version of a webcam recording.
        preview=True shows a live window during processing (useful for tuning).
        """
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

        filt = self._get_filter()
        console.print(
            f"[cyan]Rendering caricature:[/cyan] {total} frames "
            f"@ {fps:.0f} fps ({total/fps:.0f}s)"
        )
        console.print(f"  Exaggeration: {self.exaggeration}x  |  Cartoon: {self.cartoon_strength*100:.0f}%")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Applying caricature filter...", total=total)

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                processed = filt.process(frame)
                writer.write(processed)

                if preview:
                    cv2.imshow("Caricature Preview (q to quit)", processed)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                frame_idx += 1
                progress.update(task, advance=1)

        cap.release()
        writer.release()
        if preview:
            cv2.destroyAllWindows()
        filt.close()
        self._filter = None

        console.print(f"[green]Caricature video saved:[/green] {output_path}")
        return output_path

    def preview_live(self, webcam_device: int = 0) -> None:
        """
        Open the webcam and show the caricature filter live.
        Useful for tuning exaggeration before a recording session.
        Press Q to quit.
        """
        cap = cv2.VideoCapture(webcam_device)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open webcam device {webcam_device}")

        filt = self._get_filter()
        console.print("[cyan]Live caricature preview — press Q to quit[/cyan]")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            processed = filt.process(frame)
            side_by_side = np.hstack([frame, processed])
            cv2.imshow("Original | Caricature", side_by_side)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        filt.close()
        self._filter = None

    def _load_baseline(self) -> NeutralBaseline:
        path = self.baseline_dir / BASELINE_FILENAME
        if path.exists():
            console.print(f"[dim]Loaded personal baseline from {path}[/dim]")
            return NeutralBaseline.load(path)
        console.print("[dim]No personal baseline found — using generic defaults[/dim]")
        return NeutralBaseline.default()
