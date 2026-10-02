"""Plan construction, collisions, and the safety guards."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cluttercutter.planner import build_plan, unique_destination
from cluttercutter.rules import PROTECTED
from cluttercutter.scanner import scan


class TestBuildPlan:
    def test_categorised_files_are_planned(self, messy):
        plan = build_plan(scan(messy), messy)
        assert {m.src.name for m in plan.moves} >= {"holiday.jpg", "report.pdf"}
        cat = {m.src.name: m.category for m in plan.moves}
        assert cat["holiday.jpg"] == "Images"
        assert cat["report.pdf"] == "Documents"

    def test_destination_is_category_subfolder(self, messy):
        plan = build_plan(scan(messy), messy)
        for m in plan.moves:
            assert m.dst.parent.name == m.category

    def test_protected_left_alone_by_default(self, messy):
        plan = build_plan(scan(messy), messy)
        moved = {m.src.name for m in plan.moves}
        assert "unknown.qqq" not in moved
        assert "noextension" not in moved

    def test_protected_movable_when_opted_in(self, messy):
        plan = build_plan(scan(messy), messy, include_protected=True)
        moved = {m.src.name for m in plan.moves}
        assert "unknown.qqq" in moved
        target = next(m for m in plan.moves if m.src.name == "unknown.qqq")
        assert target.category == PROTECTED

    def test_no_destination_escapes_root(self, messy):
        plan = build_plan(scan(messy), messy, include_protected=True)
        for m in plan.moves:
            assert messy in m.dst.parents

    def test_build_plan_is_pure(self, messy):
        """Planning must not touch the disk."""
        before = sorted(p.name for p in messy.iterdir())
        build_plan(scan(messy), messy)
        after = sorted(p.name for p in messy.iterdir())
        assert before == after

    def test_empty_folder_gives_empty_plan(self, empty):
        plan = build_plan(scan(empty), empty)
        assert plan.moves == []

    def test_summary_counts_by_category(self, messy):
        plan = build_plan(scan(messy), messy)
        summary = plan.summary()
        assert summary["Images"] == 2   # jpg + png
        assert sum(summary.values()) == len(plan.moves)

    def test_ids_not_treated_as_extensions(self, messy):
        """.asc is unknown, so the file is protected rather than guessed at."""
        (messy / "notes.txt.asc").write_bytes(b"z" * 5)
        plan = build_plan(scan(messy), messy)
        assert "notes.txt.asc" not in {m.src.name for m in plan.moves}

        # Confirmed as protected once the user opts in.
        opted = build_plan(scan(messy), messy, include_protected=True)
        entry = next(m for m in opted.moves if m.src.name == "notes.txt.asc")
        assert entry.category == PROTECTED


class TestCollisions:
    def test_existing_destination_gets_numbered_rename(self, messy):
        target = messy / "Documents"
        target.mkdir()
        (target / "report.pdf").write_bytes(b"original")

        plan = build_plan(scan(messy), messy)
        entry = next(m for m in plan.moves if m.src.name == "report.pdf")
        assert entry.dst.name == "report (1).pdf"

    def test_collision_never_overwrites_the_existing_file(self, messy):
        target = messy / "Documents"
        target.mkdir()
        original = target / "report.pdf"
        original.write_bytes(b"original")

        from cluttercutter.mover import apply_plan
        apply_plan(build_plan(scan(messy), messy))
        assert original.read_bytes() == b"original"

    def test_two_sources_one_name_resolve_distinctly(self, tmp_path):
        root = tmp_path / "clash"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / "x.png").write_bytes(b"1")
        (root / "b" / "x.png").write_bytes(b"2")

        report = scan(root, recursive=True)
        plan = build_plan(report, root)
        names = [m.dst.name for m in plan.moves if m.src.name == "x.png"]
        assert len(set(names)) == len(names) == 2

    def test_case_variant_conflict_detected(self, messy):
        """Windows treats Report.pdf and report.pdf as one file."""
        target = messy / "Documents"
        target.mkdir()
        (target / "REPORT.PDF").write_bytes(b"upper")

        plan = build_plan(scan(messy), messy)
        entry = next(m for m in plan.moves if m.src.name == "report.pdf")
        assert entry.dst.name != "report.pdf"

    def test_unique_destination_claims_names(self, tmp_path):
        taken: set[Path] = set()
        a = unique_destination(tmp_path / "f.txt", taken)
        b = unique_destination(tmp_path / "f.txt", taken)
        assert a != b


class TestPathTraversalGuard:
    def test_path_like_category_is_refused(self, messy):
        """A category name containing path separators must be rejected.

        Guards against a rule table that later picks up a path-like name.
        """
        from cluttercutter.planner import build_plan as bp
        from cluttercutter.scanner import FileEntry, ScanReport

        entry = FileEntry(
            path=messy / "evil.txt", size=10,
            category="../escaped", modified=0.0,
        )
        plan = bp(ScanReport(entries=[entry]), messy)

        # Not a recognised category, so it is never treated as a destination.
        for m in plan.moves:
            assert ".." not in str(m.dst)