"""Applying plans, locked files, and the no-data-loss guarantees."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cluttercutter.mover import apply_plan
from cluttercutter.planner import MoveIntent, build_plan
from cluttercutter.scanner import scan


class TestApply:
    def test_moves_files_into_category_folders(self, messy):
        apply_plan(build_plan(scan(messy), messy))
        assert (messy / "Images" / "holiday.jpg").exists()
        assert (messy / "Documents" / "report.pdf").exists()
        assert not (messy / "holiday.jpg").exists()

    def test_no_files_are_deleted(self, messy):
        """Byte count in the tree must be conserved exactly."""
        def total_size(d: Path) -> int:
            return sum(
                p.stat().st_size
                for p in d.rglob("*")
                if p.is_file()
            )

        before = total_size(messy)
        apply_plan(build_plan(scan(messy), messy))
        assert total_size(messy) == before

    def test_content_survives_the_move(self, messy):
        original = (messy / "holiday.jpg").read_bytes()
        apply_plan(build_plan(scan(messy), messy))
        assert (messy / "Images" / "holiday.jpg").read_bytes() == original

    def test_protected_stay_put(self, messy):
        apply_plan(build_plan(scan(messy), messy))
        assert (messy / "unknown.qqq").exists()
        assert (messy / "noextension").exists()
        # And no Protected folder was created, because nothing went there.
        assert not (messy / "Protected").exists()

    def test_dry_run_changes_nothing(self, messy):
        before = sorted(p.name for p in messy.iterdir())
        plan = build_plan(scan(messy), messy)
        result = apply_plan(plan, dry_run=True)

        assert result.moved == []
        assert sorted(p.name for p in messy.iterdir()) == before

    def test_empty_plan_creates_no_directories(self, empty):
        apply_plan(build_plan(scan(empty), empty))
        assert list(empty.iterdir()) == []


class TestFailureIsolation:
    def test_one_locked_file_does_not_abort_the_run(self, messy):
        """The headline requirement: failures are per-file, never fatal."""
        plan = build_plan(scan(messy), messy)
        real_rename = os.rename

        def rename_with_one_locked(src, dst):
            if "holiday.jpg" in str(src):
                raise PermissionError(13, "file is in use")
            return real_rename(src, dst)

        with mock.patch("cluttercutter.mover.os.rename", rename_with_one_locked):
            result = apply_plan(plan)

        assert len(result.failed) == 1
        assert result.failed[0].path.name == "holiday.jpg"
        assert "locked" in result.failed[0].reason or "permission" in result.failed[0].reason
        assert len(result.moved) > 0
        assert not result.ok

    def test_source_still_present_after_failure(self, messy):
        plan = build_plan(scan(messy), messy)
        real_rename = os.rename

        def always_fails(src, dst):
            raise PermissionError(13, "denied")

        with mock.patch("cluttercutter.mover.os.rename", always_fails):
            result = apply_plan(plan)

        assert len(result.failed) == len(plan.moves)
        # Nothing lost.
        assert (messy / "holiday.jpg").exists()
        assert (messy / "report.pdf").exists()

    def test_vanished_source_is_reported_not_raised(self, messy):
        plan = build_plan(scan(messy), messy)
        (messy / "holiday.jpg").unlink()

        result = apply_plan(plan)
        assert any("disappeared" in f.reason for f in result.failed)

    def test_generic_oserror_is_captured(self, messy):
        plan = build_plan(scan(messy), messy)
        with mock.patch("cluttercutter.mover.os.rename",
                        side_effect=OSError(28, "no space left on device")):
            result = apply_plan(plan)
        assert len(result.failed) == len(plan.moves)
        assert "no space" in result.failed[0].reason

    def test_readonly_directory_failure_is_captured(self, tmp_path):
        root = tmp_path / "ro"
        root.mkdir()
        (root / "a.txt").write_bytes(b"data")
        plan = build_plan(scan(root), root)

        # Pretend every file is unwritable.
        with mock.patch("cluttercutter.mover.os.rename",
                        side_effect=PermissionError(13, "denied")):
            result = apply_plan(plan)
        assert result.failed and not result.ok


class TestNoOverwrite:
    def test_existing_destination_is_never_replaced(self, messy):
        target = messy / "Documents"
        target.mkdir()
        keeper = target / "report.pdf"
        keeper.write_bytes(b"PRECIOUS")

        # Force the plan to target the exact existing name.
        plan = build_plan(scan(messy), messy)
        for m in plan.moves:
            if m.src.name == "report.pdf":
                m.dst = keeper

        result = apply_plan(plan)
        assert keeper.read_bytes() == b"PRECIOUS"
        assert any("not overwriting" in f.reason for f in result.failed)

    def test_same_file_src_and_dst_is_a_noop(self, messy):
        intent = MoveIntent(
            src=messy / "holiday.jpg",
            dst=messy / "holiday.jpg",
            category="Images",
            size=1,
        )
        from cluttercutter.planner import Plan

        result = apply_plan(Plan(moves=[intent]))
        assert result.failed == []
        assert (messy / "holiday.jpg").exists()


class TestCrossDevice:
    def test_exdev_falls_back_to_copy_then_remove(self, messy):
        """A cross-device rename must still work, not crash."""
        import errno as _errno

        plan = build_plan(scan(messy), messy)
        payload = (messy / "holiday.jpg").read_bytes()

        def rename_exdev(src, dst):
            raise OSError(_errno.EXDEV, "cross-device link")

        with mock.patch("cluttercutter.mover.os.rename", rename_exdev):
            result = apply_plan(plan)

        assert result.failed == []
        assert (messy / "Images" / "holiday.jpg").read_bytes() == payload
        assert not (messy / "holiday.jpg").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="POSIX permissions test")
class TestRealLockedFile:
    def test_actually_locked_file_is_skipped(self, messy):
        """A file held open exclusively cannot be moved. Verify for real.

        Windows denies a rename on a file with an open handle. The point of
        the test is not which way the OS goes but that ClutterCutter handles
        either outcome without crashing or losing data.
        """
        import msvcrt

        from cluttercutter.planner import Plan

        target = messy / "locked.txt"
        target.write_bytes(b"busy payload")

        plan = Plan(moves=[MoveIntent(
            src=target, dst=messy / "Documents" / "locked.txt",
            category="Documents", size=target.stat().st_size,
        )])

        handle = open(target, "r+b")
        locked = False
        try:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 4)
                locked = True
            except OSError:
                pytest.skip("could not lock a byte range on this filesystem")

            # Must not raise.
            result = apply_plan(plan)
        finally:
            if locked:
                with contextlib.suppress(OSError):
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 4)
            handle.close()

        # Whether the OS allowed the move or refused it, the data is intact
        # and there is no half-written file.
        moved = messy / "Documents" / "locked.txt"
        assert not (moved.exists() and target.exists()), "file was duplicated"
        assert (moved.exists() or target.exists()), "file was lost"
        survivor = moved if moved.exists() else target
        assert survivor.read_bytes() == b"busy payload"

        if result.failed:
            assert result.failed[0].path.name == "locked.txt"