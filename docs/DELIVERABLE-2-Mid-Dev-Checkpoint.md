# Deliverable 2 — Mid-Development Checkpoint

**Project:** ClutterCutter — Automated Local Storage Manager
**Group size:** 5
**Due:** October 5, 2026
**Repository:** https://github.com/ppSpacker420/ClutterCutter
**Status:** Core application complete and functional on Windows, Linux and macOS

---

## 1. Progress Summary

### 1.1 Completion status

| Component | Status | Notes |
| --- | --- | --- |
| Requirements & design (`docs/`) | **Complete** | 20 EARS requirements, 8 design decisions, full traceability table |
| Category rules engine | **Complete** | 9 categories + Protected, data-driven table |
| Scanner | **Complete** | Hidden/system detection, symlink refusal, permission tolerance |
| Dependency detection | **Complete** | Project folders treated as atomic units |
| Planner | **Complete** | Pure function, collision-safe, path-traversal guarded |
| Mover | **Complete** | Per-file failure isolation, no-overwrite, cross-device fallback |
| CLI | **Complete** | Dry-run default, JSON output, exit-code contract |
| GUI | **Complete** | Tkinter, Apply disabled until a plan exists |
| Test suite | **Complete** | 103 tests, 861 lines across 6 files |
| Launchers & installers | **Complete** | Windows `.bat`, Linux/macOS `.sh`, one-command install |
| CI & binaries | **Complete** | Tests on 3 platforms, release artifacts published |

**Overall: the application is functionally complete.** Remaining work before
Oct 12 is demo polish and rehearsal, not core development.

### 1.2 Codebase metrics

| Metric | Value |
| --- | --- |
| Source modules | 7 files, 1,040 lines |
| Test code | 6 files, 861 lines |
| Test-to-source ratio | ~0.83 |
| Tests collected | 103 |
| Runtime dependencies | **0** (standard library only) |

### 1.3 Verified behaviour

All claims below were confirmed by execution, not by inspection.

**Local, Windows:**
- Dry-run on a 12-file test folder → 10 categorised across 8 folders, 2 ambiguous files correctly left alone, **0 files moved**
- `--apply` → 10 moved, both protected files untouched, all 12 files accounted for
- Re-run → found nothing left to do (idempotent)
- Collision test → `report.pdf` moved as `report (1).pdf`, pre-existing `report.pdf` verified byte-identical afterward
- GUI → launches from a Desktop shortcut with a stripped-down PATH, no console window appears

**CI, real Linux/macOS/Windows runners:**
- `ubuntu-latest`: **100 passed, 3 skipped**
- `windows-latest`: **102 passed, 1 skipped**
- `macos-latest`: **100 passed, 3 skipped**
- Linux launcher checks: `dry run is safe: OK`, `apply works: OK`, `dependency folders preserved: OK`, `GUI launched on a virtual display: OK`, `GUI constructed and rendered: OK`

The differing pass/skip counts are expected: the Windows-only tests (hidden
file attributes, `SYSTEM` attribute) are skipped on Unix, and the POSIX-only
symlink test is skipped on Windows. This confirms the platform-specific code
paths are genuinely exercised rather than universally skipped.

---

## 2. AI Tool Integration So Far

### 2.1 Planning — Kiro

Kiro's spec-driven workflow was used to produce the requirements before code
existed. It generates `requirements.md` in EARS notation, then `design.md`,
then `tasks.md`, each requiring human approval before proceeding.

**Delivered:** 20 EARS-format requirements (`WHEN/IF/WHILE` patterns), each
mapped to the module implementing it and the test verifying it.

**Why this matters for the assessment:** the traceability table is a visible,
auditable artifact. Any function in the codebase can be traced back to a
numbered requirement and forward to a passing test.

### 2.2 Development — Cursor

Cursor's agent mode implemented the core engine; Plan mode was used to force
a research-and-propose step before edits rather than blind generation.

**Delivered:** 7 modules implementing scanner → planner → mover, where the
first two stages never write to disk.

### 2.3 Testing — Claude test-generation agent

Generated the pytest suite with explicit instruction to target edge cases
rather than happy paths.

**Delivered:** 103 tests weighted toward failure modes — locked files, name
collisions, case-insensitive filesystem behaviour, cross-device renames,
path traversal, permission denial, cross-platform hidden-file mechanisms.

### 2.4 A note on the tool assignment

The assignment suggested Kiro for test generation. Kiro's defining constraint
is that it will not write code until a formal specification exists, which
makes it the natural fit for *requirements and design* rather than test
generation. We reassigned Kiro to planning and used Claude for tests. We
believe this produces a stronger submission because the EARS spec is a
concrete artifact an evaluator can inspect.

---

## 3. Current Roadblocks and Challenges

We are listing these honestly, including problems we caused ourselves.

### 3.1 Resolved — silent CI failure that passed while doing nothing

**The problem.** Our first published release (`v1.0.0`) attached **zero
binaries** while CI displayed a green checkmark on every job.

**Root cause.** `actions/download-artifact` strips the upload path prefix, so
binaries landed at `artifacts/cluttercutter-linux/` rather than
`artifacts/cluttercutter-linux/dist/`. Our `if [ -d ... ]` guards never
matched, so every `tar` command was skipped. The step then ran
`ls ... || true`, which swallowed the failure and exited 0.

**A second bug in the same step:** the tarball was written to `../$out` from
inside `artifacts/`, landing one directory above where the release step
looked for it.

**Resolution.** Guard on the binaries themselves rather than a directory name,
`chmod +x` them (the download does not preserve the executable bit), write to
the correct path, and `exit 1` with a diagnostic listing when a binary is
missing. Verified by downloading the published tarball back and confirming
`ELF` magic bytes and `-rwxr-xr-x` permissions.

**Lesson.** This is the single most important lesson of the project: *for a
tool that moves user files, CI status is not evidence.* A green checkmark
meant nothing; observing the asset count is what caught it.

### 3.2 Resolved — AI-generated logic inversion

**The problem.** A generated filter for non-recursive scanning was inverted,
causing the scanner to descend into subfolders when it should not have.

**Detection.** Two pre-existing tests failed immediately:
`test_non_recursive_by_default` and a collision test.

**Resolution.** The list must end up empty, not filtered. Fixed; full suite
green. Worth noting the tests that caught it were written *before* this bug
existed — direct evidence of the value of the test suite, and of why AI-written
tests still need review but are not worthless.

### 3.3 Resolved — AI test assertions that were wrong, not the code

**The problem.** Three generated tests asserted incorrect behaviour:
- `archive.tar.gz` expected to be unclassified, but classifying by final
  suffix (`.gz` → Archives) is correct behaviour
- A test read a file while holding an exclusive byte-range lock, so the
  assertion itself raised `PermissionError`
- A test asserted a loose file should *not* move, when moving loose files is
  the product's entire purpose

**Resolution.** In all three cases we corrected the **test**, after
independently determining the code was right. This is a recurring and
under-discussed failure mode: AI will confidently generate an assertion that
encodes a misreading of the spec, and — crucially — an AI-written test is not
an independent check on AI-written code.

### 3.4 Resolved — portability bug that would only appear on Windows

**The problem.** Collision detection used `Path.exists()`, which is
case-sensitive on Linux but case-insensitive on Windows. On Windows,
`report.pdf` and `REPORT.PDF` are the *same file*, so a case-variant
conflict would go undetected — meaning the tool could silently overwrite a
file on one platform but not the other.

**Resolution.** Detection now compares case-folded names on **both**
platforms. The bug would have appeared only on Windows and only with a
specifically-cased collision — exactly the kind of defect that survives casual
testing.

### 3.5 Resolved — dependency separation (design flaw, not a bug)

**The problem.** Sorting purely by extension would move `main.py` → `Code/`
and `requirements.txt` → `Documents/`, breaking `pip install -r`. An HTML page
would be separated from its CSS, JS and images.

**Resolution.** Introduced `bundles.py`: a folder containing a project marker
(`package.json`, `requirements.txt`, `pom.xml`, `Cargo.toml`, any `.html`),
or named `node_modules`/`venv`/`dist`/`assets`, is treated as **atomic** and
left entirely alone. Detection is deliberately conservative — a false negative
merely restores old behaviour, whereas a false positive would refuse to tidy a
folder of screenshots.

### 3.6 Open — cross-platform GUI verification is partial

**Status.** Ubuntu and macOS are verified in CI; Fedora, Arch and openSUSE are
not. Tkinter is a system package whose name differs per distro, and the
installer prints the correct command per distro if the GUI will not start. The
**CLI requires no tkinter** and is unaffected.

**Planned mitigation.** The standalone Linux binary bundles tkinter, so users
who download the binary rather than installing from source are not exposed to
this at all.

### 3.7 Open — no undo mechanism

If a user applies a plan and immediately regrets it, there is no journal to
reverse the moves. We judged this acceptable because **nothing is ever
deleted** — recovery is a manual drag-and-drop, not data reconstruction. It is
the first item on the deferred list and would be the top candidate for
post-presentation development.

### 3.8 RESOLVED — performance requirement failed, and the cause was a design flaw

This is the one we are most pleased to report, because the requirement failed
and we found out by measuring rather than assuming.

**The problem.** Requirement N1 states a scan of 10,000 files must complete
within 5 seconds. Our first benchmark showed **7.06 seconds — a failure.**

| Stage | Time (10,000 files) |
| --- | --- |
| Scan | 1.70 s |
| Plan | **5.37 s** |

The planning stage was three times slower than the scan.

**Root cause.** Profiling showed 48,000 calls to a Windows filesystem syscall
(`_getfinalpathname`) consuming 3.8s of the 7.5s total. The planner called
`Path.resolve()` on the destination path *for every single file*, to verify the
destination stayed inside the target folder. That is a legitimate safety check
— but it was re-deriving the same answer thousands of times, since every
destination is `root/<category>/<filename>`.

**Resolution.** The containment check now runs **once per category** at the
start of planning rather than once per file. All destinations are derived from
a validated category directory, so one check per category proves the property
for every file beneath it.

**Result:**

| Files | Scan | Plan | Total | Throughput | N1 |
| --- | --- | --- | --- | --- | --- |
| 1,000 | 0.23 s | 0.12 s | 0.34 s | 2,907/s | — |
| 10,000 | 1.92 s | 0.93 s | **2.84 s** | 3,518/s | **PASS** |
| 50,000 | 9.75 s | 4.53 s | 14.28 s | 3,503/s | — |

Planning improved **5.8×** (5.37s → 0.93s); the overall requirement now passes
with 43% headroom.

**Regression check.** All 103 tests still pass, including
`test_no_destination_escapes_root` and `test_path_like_category_is_refused` —
a hostile `../escaped` category is still refused. The safety guarantee was not
traded away for speed.

**Lesson.** We wrote a performance requirement, then nearly presented it as
satisfied without measuring. The requirement was wrong and we were wrong to
assume. Benchmarks are cheap; unverified claims in a submitted document are not.

---

## 4. Demonstration Plan for Oct 12

1. **Launch** the GUI from a Desktop shortcut — no console window (2 min)
2. **Scan** a prepared test folder containing loose files, a Python project
   and a web page (1 min)
3. **Read the preview aloud** — the proposed moves, and the "Left alone" panel
   showing the two protected files (1 min)
4. **Apply**, then show the resulting folder tree (1 min)
5. **Demonstrate the safety properties**:
   - re-run → nothing to do (idempotence)
   - collision → shows the protected-file skip
   - show that the project folder was never entered (2 min)
6. **CLI demo** — `--json` output to show the machine-readable plan (1 min)
7. **AI integration discussion** — walk the evaluator from
   `requirements.md` to a specific test (3 min)

**Contingency:** the standalone binaries are published for all three
platforms, so the demo does not depend on the evaluator's machine having
Python or the correct tkinter package.

---

## 5. Team Work Plan, Oct 5–12

| Member | Focus |
| --- | --- |
| 1 — Spec & Requirements | Rehearse the traceability walkthrough; finalise requirements traceability for presentation |
| 2 — Architecture & Core Engine | Prepare the purity-boundary explanation; review dependency detection demo |
| 3 — Scanner & Safety | Rehearse safety-property demonstrations; prepare the locked-file and collision scenarios |
| 4 — Test & QA | Produce a coverage summary; re-run `benchmarks/scan_benchmark.py` before the demo and quote the measured figures |
| 5 — Interfaces, CI & Demo | Rehearse the demo end-to-end; verify binaries on a clean machine; prepare fallback recording |

---

## 6. What We Would Do Differently

1. **Verify the release artifact, not the pipeline status.** Our first release
   shipped empty while every job was green.
2. **Write safety tests before the safety code.** The tests that caught the
   logic inversion pre-dated it.
3. **Benchmark before claiming — we did, late.** Requirement N1 was failing
   at 7.06s against a 5s target. Measuring one week before the deadline was
   too late to design against; it should have happened with the requirement.
4. **Force a clean-machine demo rehearsal.** Every GUI verification so far ran
   on a development machine with Python already installed.