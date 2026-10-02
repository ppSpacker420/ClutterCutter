"""Scan a directory and report what is in it.

Cross-platform notes:
  * Hidden/system detection differs. On Windows a file is hidden via a file
    attribute, not a leading dot, so ``desktop.ini`` and friends must be
    excluded via ``st_file_attributes``. On POSIX the leading dot is the rule.
  * Symlinks are never followed. A symlinked directory could otherwise walk
    the scan clean out of the folder the user authorised.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from .bundles import is_project_root, is_project_unit
from .rules import ORGANISED_MARKERS, categorise

# Windows file attribute bits.
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400  # symlink / junction on Windows


@dataclass
class FileEntry:
    """One file found by the scanner."""

    path: Path
    size: int
    category: str
    modified: float


@dataclass
class ScanReport:
    entries: list[FileEntry] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (name, reason)

    @property
    def total_bytes(self) -> int:
        return sum(e.size for e in self.entries)

    def by_category(self) -> dict[str, list[FileEntry]]:
        out: dict[str, list[FileEntry]] = {}
        for e in self.entries:
            out.setdefault(e.category, []).append(e)
        return out


def is_hidden_or_system(path: Path) -> bool:
    """True when the OS considers the file hidden, system, or a symlink.

    Works on both platforms. On Windows this consults the file attributes;
    on POSIX the leading-dot convention covers it. Dotfiles are treated as
    hidden on both platforms so behaviour does not change with OS.
    """
    if path.name.startswith("."):
        return True
    try:
        st = path.lstat()
    except OSError:
        # Cannot stat it - if we cannot see it, do not touch it.
        return True

    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM):
        return True
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    # POSIX: a symlink has S_IFLNK in its mode.
    if stat.S_ISLNK(st.st_mode):
        return True
    return False


def scan(
    root: Path,
    *,
    recursive: bool = False,
    skip_organised: bool = True,
) -> ScanReport:
    """Walk ``root`` and classify what we find.

    Args:
        recursive: descend into subdirectories. Off by default so a run can
            never reach further than the folder the user pointed at.
        skip_organised: ignore folders whose name matches a category, so a
            previous run's output is not reshuffled on the next run.

    Returns:
        A ScanReport of entries plus a list of skipped (name, reason) pairs.
        Unreadable files are recorded as skipped, never raised - one bad file
        must not stop a scan.
    """
    report = ScanReport()
    root = Path(root).expanduser().resolve()

    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    # If the user has pointed the tool straight at a project folder, sorting
    # its loose files would break it just as surely as splitting its
    # subfolders would. Only an explicit project marker counts here - the
    # weaker "contains a web page" heuristic is not enough, because a
    # Downloads folder that happens to hold one saved .html file should still
    # be tidied.
    if is_project_root(root):
        report.skipped.append((root.name, "this folder is a project - nothing inside it will be moved"))
        return report

    try:
        walker = os.walk(root, followlinks=False)
        for dirpath, dirnames, filenames in walker:
            here = Path(dirpath)

            if not recursive:
                # Do not descend. dirnames must end up EMPTY - os.walk
                # descends into whatever is left in it. Note a project unit
                # for the user's benefit, but do not keep it in the list.
                for d in sorted(dirnames):
                    is_unit, reason = is_project_unit(here / d)
                    if is_unit:
                        report.skipped.append((d, reason))
                dirnames[:] = []
            else:
                # Prune already-organised folders and hidden dirs in-place,
                # and never descend into a folder that is a single atomic
                # unit (a project, a web page, a venv). Sorting its files by
                # extension would separate files that depend on each other.
                keep: list[str] = []
                for d in sorted(dirnames):
                    child = here / d
                    if is_hidden_or_system(child):
                        report.skipped.append((d, "hidden/system"))
                        continue
                    if skip_organised and d.lower() in ORGANISED_MARKERS:
                        continue
                    is_unit, reason = is_project_unit(child)
                    if is_unit:
                        # Recorded, not silently dropped: the user can see
                        # what was spared and why.
                        report.skipped.append((d, reason))
                        continue
                    keep.append(d)
                dirnames[:] = keep

            for filename in sorted(filenames):
                path = here / filename

                if is_hidden_or_system(path):
                    report.skipped.append((filename, "hidden/system"))
                    continue

                try:
                    st = path.stat()
                except PermissionError:
                    report.skipped.append((filename, "permission denied"))
                    continue
                except OSError as exc:
                    report.skipped.append((filename, f"unreadable: {exc.strerror}"))
                    continue

                # Only regular files. Sockets/fifos/devices are not ours.
                if not stat.S_ISREG(st.st_mode):
                    report.skipped.append((filename, "not a regular file"))
                    continue

                report.entries.append(
                    FileEntry(
                        path=path,
                        size=st.st_size,
                        category=categorise(filename),
                        modified=st.st_mtime,
                    )
                )

    except PermissionError:
        report.skipped.append((str(root), "permission denied while walking"))

    return report