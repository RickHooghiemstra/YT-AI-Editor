from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def cleanup_raw(session_dir: Path) -> None:
    """Remove raw recordings after processing to free space."""
    if session_dir.exists():
        shutil.rmtree(session_dir)


def get_session_dir(base: Path, sid: str) -> Path:
    d = base / sid
    d.mkdir(parents=True, exist_ok=True)
    return d
