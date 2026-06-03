"""
Persistent clip library — stores every scored highlight moment across all sessions.
Used by the best-of compilation feature to pull top clips without re-analyzing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()

LIBRARY_FILE = Path("output") / "clip_library.json"


@dataclass
class LibraryClip:
    session_id: str
    game: str
    timestamp_seconds: float
    screen_file: str          # path to source screen recording
    webcam_file: str          # path to source webcam recording
    highlight_score: int
    category: str
    description: str
    energy: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LibraryClip":
        return cls(**d)

    @property
    def created_dt(self) -> datetime:
        return datetime.fromisoformat(self.created_at)

    @property
    def source_exists(self) -> bool:
        return Path(self.screen_file).exists()


class ClipLibrary:
    def __init__(self, path: Path = LIBRARY_FILE) -> None:
        self.path = path
        self._clips: list[LibraryClip] = []
        self._load()

    def add_session_highlights(
        self,
        session_id: str,
        game: str,
        screen_file: Path,
        webcam_file: Path,
        moments: list,  # list of Moment from analyzer
        min_score: int = 6,
    ) -> int:
        """Add highlight moments from a session. Returns count added."""
        added = 0
        for m in moments:
            if m.highlight_score >= min_score:
                self._clips.append(LibraryClip(
                    session_id=session_id,
                    game=game,
                    timestamp_seconds=m.timestamp_seconds,
                    screen_file=str(screen_file),
                    webcam_file=str(webcam_file),
                    highlight_score=m.highlight_score,
                    category=m.category,
                    description=m.description,
                    energy=m.energy,
                ))
                added += 1
        self._save()
        console.print(f"[green]Clip library:[/green] {added} highlights saved from session {session_id}")
        return added

    def query(
        self,
        game: Optional[str] = None,
        days: Optional[int] = None,
        min_score: int = 6,
        category: Optional[str] = None,
        limit: int = 50,
        existing_files_only: bool = True,
    ) -> list[LibraryClip]:
        """Query clips with optional filters. Returns sorted by score descending."""
        results = self._clips

        if game:
            game_lower = game.lower()
            results = [c for c in results if game_lower in c.game.lower()]

        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            results = [c for c in results if c.created_dt >= cutoff]

        results = [c for c in results if c.highlight_score >= min_score]

        if category:
            results = [c for c in results if c.category == category]

        if existing_files_only:
            results = [c for c in results if c.source_exists]

        results = sorted(results, key=lambda c: c.highlight_score, reverse=True)
        return results[:limit]

    def summary(self) -> None:
        """Print a summary table of the library."""
        table = Table(title=f"Clip Library — {len(self._clips)} clips total", show_header=True)
        table.add_column("Game", style="cyan")
        table.add_column("Clips", justify="right")
        table.add_column("Avg Score", justify="right")
        table.add_column("Latest", style="dim")

        games: dict[str, list[LibraryClip]] = {}
        for clip in self._clips:
            games.setdefault(clip.game, []).append(clip)

        for game, clips in sorted(games.items()):
            avg = sum(c.highlight_score for c in clips) / len(clips)
            latest = max(c.created_at for c in clips)[:10]
            table.add_row(game, str(len(clips)), f"{avg:.1f}", latest)

        console.print(table)

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._clips = [LibraryClip.from_dict(d) for d in data.get("clips", [])]
            except (json.JSONDecodeError, TypeError, KeyError):
                self._clips = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            {"clips": [c.to_dict() for c in self._clips]},
            indent=2,
        ))


_library: Optional[ClipLibrary] = None


def get_library() -> ClipLibrary:
    global _library
    if _library is None:
        _library = ClipLibrary()
    return _library
