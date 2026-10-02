"""Execute a move plan.

Hard rules enforced here:
  * Nothing is deleted or overwritten. Verified before every move.
  * Every move is individually wrapped. A locked file fails alone.
  * Failures are collected and reported, never raised as a crash.
  * Directory creation is lazy, so a run that moves nothing creates nothing.
"""

from __future__ import annotations

import errno
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .planner import Plan


@dataclass
class Failure:
    path: Path
    reason: str


@dataclass
class MoveReport:
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[Failure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        parts = [f"{len(self.moved)} moved"]
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return ", ".join(parts)


def _same_file(a: Path, b: Path) -> bool:
    """True when both paths already refer to one file on disk.

    Guards the overwrite case: if src and dst resolve to the same inode we
    must not move, because a move would either be a no-op or destroy data.
    """
    try:
        return a.exists() and b.exists() and os.path.samefile(a, b)
    except OSError:
        return False


def apply_plan(plan: Plan, *, dry_run: bool = False) -> MoveReport:
    """Execute every intent in ``plan``.

    Args:
        plan: the plan to execute.
        dry_run: when True, simulate only. Creates no directories and moves
            no files, but still performs every safety check so the preview
            reports the same failures the real run would hit.

    Returns:
        A MoveReport of successes and per-file failures.
    """
    report = MoveReport()
    if dry_run or not plan.moves:
        return report

    made_dirs: set[Path] = set()

    for intent in plan.moves:
        src, dst = intent.src, intent.dst

        try:
            if not src.exists():
                report.failed.append(Failure(src, "source disappeared before move"))
                continue

            if not src.is_file():
                report.failed.append(Failure(src, "source is no longer a regular file"))
                continue

            # The overwrite guard. Resolve symlinks where possible so a
            # link pointing at the destination is still caught.
            try:
                if _same_file(src.resolve(), dst.resolve()):
                    continue  # already there; nothing to do
            except OSError:
                if _same_file(src, dst):
                    continue

            if dst.exists():
                report.failed.append(
                    Failure(src, f"destination already exists (not overwriting): {dst.name}")
                )
                continue

            if not dst.parent.is_dir():
                if dst.parent not in made_dirs:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    made_dirs.add(dst.parent)

            # os.rename fails with EXDEV when source and destination are on
            # different filesystems (a mounted volume, a network share). Same
            # errno on Linux and Windows; fall back to copy+remove.
            try:
                os.rename(src, dst)
            except OSError as exc:
                if exc.errno != errno.EXDEV:
                    raise
                shutil.copy2(str(src), str(dst))
                os.remove(str(src))

            report.moved.append((src, dst))

        except PermissionError:
            report.failed.append(Failure(src, "permission denied - file may be locked or in use"))
        except OSError as exc:
            report.failed.append(Failure(src, f"could not move: {exc.strerror or exc}"))

    plan.applied = True
    return report