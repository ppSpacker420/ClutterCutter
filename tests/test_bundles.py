"""Dependency safety: files that must not be separated.

The rule under test: a folder whose parts depend on each other is an atomic
unit. ClutterCutter either moves all of it or none of it, and in practice
"none" - it leaves the folder completely alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cluttercutter.bundles import UNIT_NAMES, is_project_root, is_project_unit
from cluttercutter.mover import apply_plan
from cluttercutter.planner import build_plan
from cluttercutter.scanner import scan


def make(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


class TestIsProjectUnit:
    def test_python_project_is_a_unit(self, tmp_path):
        f = make(tmp_path / "proj", {
            "requirements.txt": "flask\n",
            "main.py": "print(1)",
            "utils.py": "x = 1",
        })
        assert is_project_unit(f)[0] is True

    def test_node_project_is_a_unit(self, tmp_path):
        f = make(tmp_path / "web", {"package.json": "{}", "app.js": "x"})
        assert is_project_unit(f)[0] is True

    def test_web_page_folder_is_a_unit(self, tmp_path):
        """The exact case: html needs its sibling css/js/images."""
        f = make(tmp_path / "site", {
            "index.html": "<link rel=stylesheet href=style.css>",
            "style.css": "body{}",
            "app.js": "console.log(1)",
            "logo.png": "PNG",
        })
        assert is_project_unit(f)[0] is True

    def test_html_only_folder_is_a_unit(self, tmp_path):
        assert is_project_unit(make(tmp_path / "p", {"page.html": "<p>"}))[0] is True

    @pytest.mark.parametrize("name", sorted(UNIT_NAMES))
    def test_self_contained_names_are_units(self, tmp_path, name):
        f = tmp_path / name
        f.mkdir()
        assert is_project_unit(f)[0] is True

    def test_plain_folder_is_not_a_unit(self, tmp_path):
        """A folder of loose downloads must still get tidied."""
        f = make(tmp_path / "stuff", {
            "a.png": "x", "b.pdf": "y", "notes.txt": "z", "c.mp3": "w",
        })
        assert is_project_unit(f)[0] is False

    def test_reason_is_human_readable(self, tmp_path):
        f = make(tmp_path / "p", {"requirements.txt": "x"})
        _, reason = is_project_unit(f)
        assert "project" in reason.lower()
        assert "requirements.txt" in reason


class TestIsProjectRoot:
    def test_root_with_marker_is_protected(self, tmp_path):
        f = make(tmp_path / "proj", {"package.json": "{}", "main.py": "x"})
        assert is_project_root(f) is True

    def test_root_with_only_html_is_still_sortable(self, tmp_path):
        """Strictness matters: a Downloads folder holding one saved HTML
        page should not be treated as a project."""
        f = make(tmp_path / "Downloads", {
            "page.html": "<p>", "a.png": "x", "b.pdf": "y",
        })
        assert is_project_root(f) is False


class TestRecursiveScanRespectsUnits:
    def test_html_and_its_assets_stay_together(self, tmp_path):
        """The scenario from the request, end to end."""
        root = make(tmp_path / "Downloads", {
            "site/index.html": "<link rel=stylesheet href=style.css>",
            "site/style.css": "body{}",
            "site/app.js": "x",
            "site/logo.png": "PNG",
            "loose.pdf": "doc",
        })

        report = scan(root, recursive=True)
        moved = {e.path.name for e in report.entries}

        assert "loose.pdf" in moved
        # None of the web project's files are individually sortable.
        for name in ("index.html", "style.css", "app.js", "logo.png"):
            assert name not in moved, f"{name} was separated from its project"

    def test_python_project_stays_together(self, tmp_path):
        root = make(tmp_path / "Downloads", {
            "myproj/requirements.txt": "flask",
            "myproj/main.py": "print(1)",
            "myproj/config.yaml": "a: 1",
        })

        report = scan(root, recursive=True)
        moved = {e.path.name for e in report.entries}
        # requirements.txt would otherwise land in Documents/.
        assert "requirements.txt" not in moved
        assert "main.py" not in moved

    def test_unit_is_reported_not_silently_dropped(self, tmp_path):
        root = make(tmp_path / "Downloads", {
            "myproj/requirements.txt": "flask",
            "loose.pdf": "doc",
        })
        report = scan(root, recursive=True)
        reasons = dict((n, r) for n, r in report.skipped)
        assert "myproj" in reasons
        assert "project" in reasons["myproj"].lower()

    def test_venv_contents_not_scanned(self, tmp_path):
        root = make(tmp_path / "Downloads", {
            ".venv/lib/pkg/module.py": "x",
            ".venv/pyvenv.cfg": "",
            "loose.pdf": "doc",
        })
        report = scan(root, recursive=True)
        assert "module.py" not in {e.path.name for e in report.entries}
        assert "loose.pdf" in {e.path.name for e in report.entries}

    def test_ordinary_subfolder_still_sorted(self, tmp_path):
        """We must not be so cautious that nothing ever gets organised."""
        root = make(tmp_path / "Downloads", {
            "photos/a.png": "x", "photos/b.jpg": "y",
            "loose.pdf": "doc",
        })
        report = scan(root, recursive=True)
        moved = {e.path.name for e in report.entries}
        assert {"a.png", "b.jpg", "loose.pdf"} <= moved


class TestProjectRootProtection:
    def test_pointing_at_a_project_moves_nothing(self, tmp_path):
        root = make(tmp_path / "myproj", {
            "package.json": "{}",
            "index.html": "<p>",
            "style.css": "body{}",
            "README.md": "# hi",
        })

        plan = build_plan(scan(root, recursive=True), root)
        assert plan.moves == []

    def test_pointing_at_downloads_still_works(self, tmp_path):
        root = make(tmp_path / "Downloads", {
            "a.pdf": "x", "b.png": "y", "c.mp3": "z",
        })
        plan = build_plan(scan(root), root)
        assert len(plan.moves) == 3


class TestApplyKeepsUnitsWhole:
    def test_nothing_inside_a_project_moves_on_apply(self, tmp_path):
        """Every file in the project subfolder keeps its exact path.

        The loose file at the root is expected to move - tidying loose files
        is the entire point of the tool.
        """
        root = make(tmp_path / "Downloads", {
            "site/index.html": "<p>",
            "site/style.css": "body{}",
            "site/logo.png": "PNG",
            "loose.pdf": "doc",
        })

        project_files = {
            "site/index.html": b"<p>",
            "site/style.css": b"body{}",
            "site/logo.png": b"PNG",
        }

        apply_plan(build_plan(scan(root, recursive=True), root))

        for rel, content in project_files.items():
            assert (root / rel).exists(), f"{rel} moved or was lost"
            assert (root / rel).read_bytes() == content, f"{rel} was modified"

    def test_project_in_downloads_survives_a_run(self, tmp_path):
        root = make(tmp_path / "Downloads", {
            "site/index.html": "<p>",
            "site/style.css": "body{}",
            "loose.pdf": "doc",
            "loose2.png": "x",
        })

        apply_plan(build_plan(scan(root, recursive=True), root))

        # The loose files were tidied...
        assert (root / "Documents" / "loose.pdf").exists()
        assert (root / "Images" / "loose2.png").exists()
        # ...and the project was not touched.
        assert (root / "site" / "index.html").exists()
        assert (root / "site" / "style.css").exists()