"""Benchmark the scanner against the N1 performance requirement.

N1 states: a scan of 10,000 files SHALL complete within 5 seconds.

Run:  python benchmarks/scan_benchmark.py
"""

from __future__ import annotations

import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cluttercutter.planner import build_plan
from cluttercutter.scanner import scan

# A realistic spread of extensions rather than 10,000 copies of one type.
EXTENSIONS = [
    ".jpg", ".png", ".pdf", ".txt", ".mp4", ".mp3", ".zip", ".py",
    ".xlsx", ".pptx", ".docx", ".json", ".csv", ".yaml", ".toml",
]


def populate(root: Path, count: int) -> None:
    """Create ``count`` small files spread across a few subdirectories."""
    subdirs = [root / f"d{i}" for i in range(20)]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        ext = EXTENSIONS[i % len(EXTENSIONS)]
        target = subdirs[i % len(subdirs)] / f"file_{i}{ext}"
        target.write_bytes(b"x" * 64)


def run_once(root: Path) -> tuple[float, float, int, int]:
    t0 = time.perf_counter()
    report = scan(root, recursive=True)
    t1 = time.perf_counter()
    plan = build_plan(report, root)
    t2 = time.perf_counter()
    return t1 - t0, t2 - t1, len(report.entries), len(plan.moves)


def main() -> int:
    counts = (1_000, 10_000, 50_000)

    print(f"platform: {platform.system()} {platform.machine()}")
    print(f"python:   {platform.python_version()}")
    print()
    print(f"{'files':>8} {'scan (s)':>10} {'plan (s)':>10} {'total (s)':>10} "
          f"{'files/s':>10}  N1 (10k < 5s)")
    print("-" * 66)

    root = Path(tempfile.mkdtemp(prefix="cc_bench_"))
    try:
        for count in counts:
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            populate(root, count)

            # Warm up so the first run is not penalised by import/import-cache
            # effects.
            run_once(root)

            scan_s, plan_s, entries, moves = run_once(root)
            total = scan_s + plan_s
            rate = entries / total if total else float("inf")
            verdict = ""
            if count == 10_000:
                verdict = "PASS" if total < 5.0 else "FAIL"
            print(f"{entries:>8} {scan_s:>10.3f} {plan_s:>10.3f} {total:>10.3f} "
                  f"{rate:>10,.0f}  {verdict}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    print("Note: files are tiny (64 bytes). A real Downloads folder has larger")
    print("files, and I/O time would dominate. This measures the metadata walk,")
    print("which is what the planner operates on.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())