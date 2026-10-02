"""Command line interface.

Safety default: with no flags, this is a dry run. ``--apply`` is required to
move anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .mover import apply_plan
from .planner import build_plan
from .scanner import scan


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cluttercutter",
        description=(
            "Automated local storage manager. Scans a folder, categorises "
            "files, and moves them into per-category subfolders. "
            "Nothing is deleted or overwritten."
        ),
    )
    p.add_argument("folder", help="the folder to scan (must be an explicit path)")
    p.add_argument("--apply", action="store_true",
                   help="actually move files. Without this, nothing changes.")
    p.add_argument("--include-protected", action="store_true",
                   help="also move files whose type could not be identified")
    p.add_argument("--recursive", action="store_true",
                   help="descend into subfolders (off by default)")
    p.add_argument("--yes", action="store_true",
                   help="skip the confirmation prompt when applying")
    p.add_argument("--json", action="store_true", help="emit the plan as JSON")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _print_plan(plan, root: Path, out) -> None:
    print(f"\nClutterCutter scan of {root}", file=out)
    print("=" * 60, file=out)

    if not plan.moves:
        print("Nothing to move.", file=out)
    else:
        for category, count in plan.summary().items():
            print(f"  {category:<15} {count} file(s)", file=out)
        print("-" * 60, file=out)
        print(f"  {len(plan.moves)} file(s), {human(plan.total_bytes)} total", file=out)
        print(file=out)
        for m in plan.moves:
            print(f"    {m.src.name}  ->  {m.dst.parent.name}/{m.dst.name}", file=out)

    if plan.skips:
        print(file=out)
        print(f"  Left alone ({len(plan.skips)}):", file=out)
        for s in plan.skips:
            print(f"    {s.path.name}  ({s.reason})", file=out)


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    out = sys.stdout

    root = Path(args.folder).expanduser()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    report = scan(root, recursive=args.recursive)
    plan = build_plan(report, root, include_protected=args.include_protected)

    if args.json:
        import json

        json.dump(
            {
                "root": str(root),
                "dry_run": not args.apply,
                "moves": [
                    {"from": str(m.src), "to": str(m.dst),
                     "category": m.category, "bytes": m.size}
                    for m in plan.moves
                ],
                "skipped": [
                    {"path": str(s.path), "reason": s.reason} for s in plan.skips
                ],
                "scan_skipped": [
                    {"name": n, "reason": r} for n, r in report.skipped
                ],
            },
            sys.stdout,
            indent=2,
        )
        print()
        return 0

    _print_plan(plan, root, out)

    if report.skipped:
        print(file=out)
        print(f"  {len(report.skipped)} item(s) left untouched:", file=out)
        for name, reason in report.skipped:
            print(f"    {name}  ({reason})", file=out)

    if not args.apply:
        print("\nDRY RUN - nothing was changed. Re-run with --apply to execute.", file=out)
        return 0

    if not plan.moves:
        print("\nNothing to apply.", file=out)
        return 0

    if not args.yes:
        answer = input(f"\nMove {len(plan.moves)} file(s)? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted. Nothing was changed.", file=out)
            return 1

    result = apply_plan(plan)
    print(f"\nDone: {result.summary()}", file=out)
    for f in result.failed:
        print(f"  FAILED {f.path.name}: {f.reason}", file=out)
    if not result.ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())