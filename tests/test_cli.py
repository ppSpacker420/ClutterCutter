"""End-to-end CLI behaviour, especially the dry-run default."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cluttercutter.cli import main


def run(*argv) -> int:
    return main(list(argv))


class TestDryRunDefault:
    def test_no_flags_changes_nothing(self, messy, capsys):
        before = sorted(p.name for p in messy.iterdir())
        rc = run(str(messy))
        assert rc == 0
        assert sorted(p.name for p in messy.iterdir()) == before
        assert not (messy / "Images").exists()

    def test_output_declares_it_is_a_dry_run(self, messy, capsys):
        run(str(messy))
        assert "DRY RUN" in capsys.readouterr().out

    def test_preview_lists_the_moves(self, messy, capsys):
        run(str(messy))
        out = capsys.readouterr().out
        assert "holiday.jpg" in out
        assert "Images" in out


class TestApply:
    def test_apply_moves_files(self, messy, capsys):
        rc = run(str(messy), "--apply", "--yes")
        assert rc == 0
        assert (messy / "Images" / "holiday.jpg").exists()
        assert "Done" in capsys.readouterr().out

    def test_decline_confirmation_moves_nothing(self, messy, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _="": "n")
        before = sorted(p.name for p in messy.iterdir())
        rc = run(str(messy), "--apply")
        assert rc == 1
        assert sorted(p.name for p in messy.iterdir()) == before

    def test_accept_confirmation_moves(self, messy, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _="": "y")
        assert run(str(messy), "--apply") == 0
        assert (messy / "Images" / "holiday.jpg").exists()

    def test_include_protected_flag(self, messy):
        run(str(messy), "--apply", "--yes", "--include-protected")
        assert (messy / "Protected" / "unknown.qqq").exists()


class TestJsonOutput:
    def test_valid_json(self, messy, capsys):
        run(str(messy), "--json")
        data = json.loads(capsys.readouterr().out)
        assert data["dry_run"] is True
        assert data["root"] == str(messy.resolve())
        assert any(m["category"] == "Images" for m in data["moves"])

    def test_json_reports_skips(self, messy, capsys):
        run(str(messy), "--json")
        data = json.loads(capsys.readouterr().out)
        assert any("unclassified" in s["reason"] for s in data["skipped"])


class TestErrors:
    def test_missing_folder_exits_nonzero(self, tmp_path, capsys):
        rc = run(str(tmp_path / "nope"))
        assert rc == 2
        assert "not a directory" in capsys.readouterr().err

    def test_file_instead_of_folder_rejected(self, tmp_path, capsys):
        f = tmp_path / "afile.txt"
        f.write_text("x")
        assert run(str(f)) == 2

    def test_empty_folder_succeeds_with_nothing_to_do(self, empty, capsys):
        assert run(str(empty)) == 0
        assert "Nothing to move" in capsys.readouterr().out


class TestModuleEntryPoint:
    def test_runs_as_python_dash_m(self, messy):
        """The documented `python -m cluttercutter` path must work."""
        proc = subprocess.run(
            [sys.executable, "-m", "cluttercutter", str(messy)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0
        assert "DRY RUN" in proc.stdout
        assert not (messy / "Images").exists()