"""Shared fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def messy(tmp_path: Path) -> Path:
    """A folder with one file of several types, plus protected ones."""
    root = tmp_path / "Downloads"
    root.mkdir()
    files = {
        "holiday.jpg": 1200,
        "screenshot.png": 3400,
        "clip.mp4": 88_000_000,
        "song.mp3": 3_100_000,
        "report.pdf": 51_000,
        "notes.txt": 800,
        "data.xlsx": 12_400,
        "deck.pptx": 44_000,
        "backup.zip": 5_000_000,
        "main.py": 2_200,
        "unknown.qqq": 640,
        "noextension": 100,
        ".hiddenfile": 50,
        ".gitignore": 30,
    }
    for name, size in files.items():
        p = root / name
        p.write_bytes(b"x" * size)
    return root


@pytest.fixture
def empty(tmp_path: Path) -> Path:
    d = tmp_path / "empty"
    d.mkdir()
    return d