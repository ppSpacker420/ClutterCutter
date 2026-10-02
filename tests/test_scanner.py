"""Scanner and classifier behaviour."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cluttercutter.rules import PROTECTED, categorise
from cluttercutter.scanner import is_hidden_or_system, scan


class TestCategorise:
    @pytest.mark.parametrize("name,expected", [
        ("holiday.jpg", "Images"),
        ("SONG.MP3", "Audio"),          # extension case must not matter
        ("report.pdf", "Documents"),
        ("data.xlsx", "Spreadsheets"),
        ("deck.pptx", "Presentations"),
        ("backup.zip", "Archives"),
        ("main.py", "Code"),
        ("font.woff2", "Fonts"),
        ("clip.mkv", "Video"),
    ])
    def test_known_extensions(self, name, expected):
        assert categorise(name) == expected

    @pytest.mark.parametrize("name", [
        "unknown.qqq",       # unrecognised
        "noextension",       # no dot
        ".gitignore",        # dotfile, dot is not an extension
        "",
    ])
    def test_unclassified_is_protected(self, name):
        assert categorise(name) == PROTECTED

    def test_windows_path_separator_handled(self):
        assert categorise(r"C:\Users\me\photo.png") == "Images"


class TestScan:
    def test_finds_regular_files(self, messy):
        report = scan(messy)
        names = {e.path.name for e in report.entries}
        assert "holiday.jpg" in names
        assert "main.py" in names

    def test_hidden_files_are_excluded(self, messy):
        report = scan(messy)
        names = {e.path.name for e in report.entries}
        assert ".hiddenfile" not in names
        assert ".gitignore" not in names

    def test_hidden_files_reported_as_skipped_not_silent(self, messy):
        report = scan(messy)
        skipped = {n for n, _ in report.skipped}
        assert ".gitignore" in skipped

    def test_empty_folder_returns_no_entries(self, empty):
        report = scan(empty)
        assert report.entries == []

    def test_non_recursive_by_default(self, messy):
        (messy / "sub").mkdir()
        (messy / "sub" / "nested.png").write_bytes(b"y" * 10)
        report = scan(messy)
        names = {e.path.name for e in report.entries}
        assert "nested.png" not in names

    def test_recursive_finds_nested(self, messy):
        (messy / "sub").mkdir()
        (messy / "sub" / "nested.png").write_bytes(b"y" * 10)
        report = scan(messy, recursive=True)
        names = {e.path.name for e in report.entries}
        assert "nested.png" in names

    def test_missing_folder_raises(self, tmp_path):
        with pytest.raises(NotADirectoryError):
            scan(tmp_path / "does_not_exist")

    def test_directory_named_like_a_file_is_skipped(self, messy):
        # A directory should never be reported as a movable file.
        (messy / "looks_like.pdf").mkdir()
        report = scan(messy)
        assert "looks_like.pdf" not in {e.path.name for e in report.entries}

    def test_total_bytes_matches_sum(self, messy):
        report = scan(messy)
        assert report.total_bytes == sum(e.size for e in report.entries)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows hidden attribute")
    def test_windows_hidden_attribute_is_respected(self, messy):
        # Windows marks files hidden via an attribute, not a leading dot.
        # A dotfile check alone would miss this one.
        target = messy / "attributed_hidden.txt"
        target.write_text("secret")
        assert not is_hidden_or_system(target)
        ctypes_set_hidden(target)
        assert is_hidden_or_system(target)

        report = scan(messy)
        assert "attributed_hidden.txt" not in {e.path.name for e in report.entries}


def ctypes_set_hidden(path: Path) -> None:
    import ctypes

    ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x2)  # FILE_ATTRIBUTE_HIDDEN


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
class TestWindowsHiddenAttribute:
    def test_system_attribute_also_respected(self, messy):
        import ctypes

        target = messy / "system_file.txt"
        target.write_text("sys")
        ctypes.windll.kernel32.SetFileAttributesW(str(target), 0x4)  # SYSTEM
        assert is_hidden_or_system(target)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only test")
class TestPosixSymlinks:
    def test_symlinked_file_is_not_followed(self, messy):
        link = messy / "link.png"
        try:
            os.symlink(messy / "holiday.jpg", link)
        except OSError:
            pytest.skip("symlinks unavailable")
        report = scan(messy)
        assert "link.png" not in {e.path.name for e in report.entries}