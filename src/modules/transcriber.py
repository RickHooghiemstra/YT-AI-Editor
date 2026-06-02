"""
Local speech-to-text using faster-whisper.
Downloads model on first run (~1.5 GB for 'large-v3', ~150 MB for 'base').
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

WhisperModel = Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"]


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: list[dict]

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "words": self.words,
        }


@dataclass
class Transcript:
    segments: list[TranscriptSegment]
    language: str
    duration: float

    @property
    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "duration": self.duration,
            "full_text": self.full_text,
            "segments": [s.to_dict() for s in self.segments],
        }

    def excerpt(self, max_chars: int = 3000) -> str:
        text = self.full_text
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Transcript":
        data = json.loads(path.read_text())
        segments = [
            TranscriptSegment(
                start=s["start"],
                end=s["end"],
                text=s["text"],
                words=s.get("words", []),
            )
            for s in data["segments"]
        ]
        return cls(
            segments=segments,
            language=data["language"],
            duration=data["duration"],
        )


def transcribe(
    audio_path: Path,
    model_size: WhisperModel = "base",
    device: str = "auto",
    language: str | None = None,
) -> Transcript:
    """
    Transcribe audio file using faster-whisper.
    model_size: 'tiny' (fast), 'base', 'small', 'medium', 'large-v3' (best)
    device: 'auto' detects CUDA/CPU automatically
    """
    try:
        from faster_whisper import WhisperModel as FasterWhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper not installed. Run: pip install faster-whisper"
        )

    if device == "auto":
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = "float16" if device == "cuda" else "int8"

    console.print(f"[cyan]Loading Whisper {model_size} model on {device}...[/cyan]")
    console.print("[dim](First run downloads the model — this is one-time)[/dim]")

    model = FasterWhisperModel(model_size, device=device, compute_type=compute_type)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Transcribing audio...", total=None)

        segments_raw, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        segments = list(segments_raw)
        progress.update(task, completed=True)

    transcript_segments = []
    for seg in segments:
        words = []
        if seg.words:
            words = [{"word": w.word, "start": w.start, "end": w.end, "prob": w.probability} for w in seg.words]
        transcript_segments.append(TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=seg.text,
            words=words,
        ))

    duration = info.duration if info.duration else (segments[-1].end if segments else 0.0)

    console.print(
        f"[green]Transcription complete[/green] — "
        f"{len(transcript_segments)} segments, language: {info.language}"
    )

    return Transcript(
        segments=transcript_segments,
        language=info.language,
        duration=duration,
    )
