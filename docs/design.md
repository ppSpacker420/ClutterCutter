# Design — ClutterCutter

## Architecture

A four-stage pipeline. Each stage has exactly one job and one output data
type. The stages that can touch the disk are quarantined at the end, and the
stage that touches it is unreachable without an explicit flag.

```
   target folder
        |
        v
   [ scanner ]  --ScanReport-->  no disk writes
        |
        v
   [ planner ]  --Plan-------->  no disk writes
        |
        v
   [  mover  ]  --MoveReport-->  writes only if apply=True
```

```
cluttercutter/
  rules.py     category table + categorise()      pure
  scanner.py   walk the tree, build ScanReport   reads only
  planner.py   ScanReport -> Plan                pure
  mover.py     Plan -> MoveReport                writes
  cli.py       argparse front end
  gui.py       Tkinter front end
```

Both front ends call the same three functions in the same order. There is no
CLI-only behaviour and no GUI-only behaviour, so a bug cannot exist in one
interface and not the other.

## Key design decisions

### D1 — The preview and the execution share one code path

`build_plan()` is pure. The preview is a `Plan` rendered as text or table
rows; the execution consumes that identical `Plan`. A dry run cannot drift
from a real run because there is only one planner.

**Rejected alternative:** computing a separate "preview" projection, e.g. by
re-running the classifier with preview flags. This would be a second source of
truth and could disagree with the real run.

### D2 — Dry-run is the absence of a flag, not the presence of one

`apply_plan()` takes `dry_run: bool`. The CLI only passes `False` when the user
typed `--apply`. The default state of the system is therefore "preview".

This is the opposite of a `--dry-run` flag, where forgetting the flag means
destroying data. Inverting the polarity moves the failure mode from silent
data loss to a harmless no-op.

### D3 — Purity boundary as the safety mechanism

`scanner` and `planner` never write. This makes the entire preview phase
trivially testable — a test asserts the directory listing is unchanged after
planning — and it means a crash during preview cannot damage anything.

### D4 — Per-file failure isolation

Every single move is wrapped individually. One locked file produces one entry
in `MoveReport.failed`; the remaining moves proceed.

```
for intent in plan.moves:
    try:
        move(intent)
    except PermissionError:  record and continue
    except OSError:          record and continue
```

**Rejected alternative:** wrap the whole loop in one `try`. A single failure
then aborts the run, and the user is left with a half-organised folder and no
idea which files moved.

### D5 — Never overwrite, decided in the planner

Collision handling lives in `unique_destination()`, so the `Plan` already
contains conflict-free destinations. The mover re-checks before each move
because state can change between planning and applying — the file may have
appeared in the interim. Defence in depth: the planner prevents the conflict,
the mover refuses it if it still exists.

### D6 — Case-insensitive collision detection on every platform

Windows treats `Report.pdf` and `report.pdf` as one filename. Checking
`Path.exists()` alone would miss that conflict on Windows while catching it on
Linux — a portability bug in the dangerous direction, where a file could be
silently overwritten. The planner instead probes the parent directory and
compares case-folded names on both platforms.

### D7 — The category table is data, not code

`rules.py` holds a dict of category → extensions and a precomputed reverse
map. Adding a file type is a one-line edit with no logic change, and the whole
table can be displayed on screen during a demo.

### D8 — Protected as a real safety category

An unrecognised extension does not get a best-guess category. It goes to
Protected, and Protected is **not moved** unless the user passes
`--include-protected`. The tool prefers to leave a file alone over guessing.

## Cross-platform notes

| Concern | Windows | Linux | Handling |
| --- | --- | --- | --- |
| Hidden files | File attribute bit | Leading dot | `is_hidden_or_system()` checks both, so behaviour is identical |
| Cross-device rename | `EXDEV` | `EXDEV` | Falls back to `copy2` + `remove` |
| Name collisions | Case-insensitive | Case-sensitive | Case-folded comparison on both, per D6 |
| Symlinks | Reparse point | `S_ISLNK` | Both detected via `st_file_attributes` / `st_mode`; never followed |

## Safety argument

The four properties that matter, and where each is enforced:

1. **No deletion.** No code path calls `unlink` or `rmdir` on a user file. The
   only `os.remove` is in the cross-device fallback, immediately after a
   successful copy to the destination.
2. **No overwrite.** Enforced at plan time (D5) and re-checked at apply time.
3. **Preview by default.** D2.
4. **Bounded blast radius.** Destinations are verified to be descendants of the
   target folder (R3.4); recursion is off by default (R1.3); Protected is
   skipped by default (R4.3).