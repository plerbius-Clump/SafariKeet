from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "SafaraKeet"
MAX_AUDIO_BYTES = int(os.getenv("SAFARAKEET_MAX_AUDIO_BYTES", 40 * 1024 * 1024))


def data_dir() -> Path:
    configured = os.getenv("SAFARAKEET_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Library" / "Application Support" / APP_NAME


def database_path() -> Path:
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path / "history.sqlite3"
