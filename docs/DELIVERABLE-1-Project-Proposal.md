# Deliverable 1 — Project Proposal

**Project:** ClutterCutter — Automated Local Storage Manager
**Group size:** 5
**Due:** September 28, 2026
**Repository:** https://github.com/ppSpacker420/ClutterCutter

---

## 1. Proposed Software Application Concept

### 1.1 Problem statement

A typical user's Downloads folder becomes a dumping ground. Files accumulate
with no organisation: screenshots beside installers beside scanned receipts
beside a half-finished project. Manually sorting this is tedious, and users
defer it indefinitely because the risk of losing or overwriting something
outweighs the tidiness benefit.

Existing cleaners solve this by being **too powerful**. They offer rules,
schedules, duplicate deletion, and cloud upload. The user's real need is
narrower: *sort the loose files by type, and do it without risking anything.*

### 1.2 Proposed solution

**ClutterCutter** is a desktop application that scans a user-specified folder,
classifies each file by its type, and moves it into a per-category subfolder
(Images, Video, Audio, Documents, Spreadsheets, Presentations, Archives, Code,
Fonts).

The differentiator is that safety is architectural, not a setting. Five
properties are enforced in code and covered by automated tests:

| Property | Enforcement |
| --- | --- |
| Dry-run is the default | The `--apply` flag is opt-in; omitting it changes nothing |
| Nothing is deleted | No code path removes a user file |
| Nothing is overwritten | Collisions resolve to `report (1).pdf`; the original is untouched |
| Ambiguous files are left alone | Unrecognised types go to `Protected` and are not moved without explicit consent |
| Working folders are atomic | Project folders, web pages and virtual environments are never split |

That last property came directly out of development. An early version sorted
by file extension and would have moved `main.py` to `Code/` while sending
`requirements.txt` to `Documents/` — silently breaking `pip install -r`. The
fix was to treat a folder containing project markers (`package.json`,
`requirements.txt`, `pom.xml`, any `.html` page) as one indivisible unit.

### 1.3 Target users

- Users with cluttered Downloads/Desktop folders
- Students and developers with many small project folders
- Non-technical users who need a GUI rather than a command line

### 1.4 Scope

**In scope**
- Recursive directory scanning with hidden/system file detection
- Extension-based classification (configurable table)
- Pure planner producing a reviewable move list
- Execution engine with per-file failure isolation
- CLI interface (Windows, Linux, macOS)
- Tkinter GUI over the identical engine
- Cross-device move fallback (`EXDEV`)
- Automated test suite (103 tests)
- CI building binaries for all three platforms

**Out of scope**
- Content-based classification by magic bytes
- Duplicate detection
- Cloud sync or backup
- Undo/journal of applied moves
- Scheduled/automated runs

### 1.5 Technical architecture

A four-stage pipeline where the stages that write to disk are quarantined
behind an explicit flag:

```
target folder --> [ scanner ] --ScanReport--> [ planner ] --Plan--> [ mover ] --> moves
                      reads only              pure function      writes, only if apply=True
```

| Module | Responsibility | Disk access |
| --- | --- | --- |
| `rules.py` | Category table and `categorise()` | none (pure) |
| `scanner.py` | Walk tree, build `ScanReport` | reads |
| `planner.py` | `ScanReport` → `Plan` | none (pure) |
| `mover.py` | `Plan` → `MoveReport` | writes |
| `cli.py` / `gui.py` | Front ends | via engine |

Because the planner is pure, **the preview and the execution share one code
path** — a dry run cannot drift from a real run because there is only one
planner. Both front ends call the same three functions, so no behaviour can
exist in the GUI that contradicts the CLI.

**Technology:** Python 3.10+, standard library only (no runtime
dependencies). Tkinter for the GUI. This was a deliberate choice: eliminating
dependencies removes an entire class of setup failures during a live demo.

### 1.6 User flows

**GUI**
1. Launch → window opens with an empty, disabled Apply button
2. Choose a folder (picker or typed path) → **Scan**
3. Preview table lists every proposed move: file, category, size, destination
4. A separate "Left alone" panel lists skipped files with reasons
5. **Apply moves** → confirmation dialog states the folder and file count
6. Results reported, including any per-file failures

**CLI**
1. `cluttercutter ~/Downloads` → preview only, states "DRY RUN — nothing was changed"
2. `cluttercutter ~/Downloads --apply` → prompts for confirmation
3. `cluttercutter ~/Downloads --apply --json` → machine-readable plan

---

## 2. Target AI Tools

| Stage | Tool | Role in our SDLC | Concrete artifact produced |
| --- | --- | --- | --- |
| **A. Planning** | **Kiro** (AWS) — spec-driven agentic IDE | Generates structured specifications before any code exists. Its three-phase workflow produces `requirements.md` in **EARS notation** (the aerospace/safety-critical standard), then `design.md`, then `tasks.md`, each requiring human approval before the next. | `docs/requirements.md` — 20 EARS requirements with a **requirement → module → test traceability table** |
| **B. Development** | **Cursor** — AI agent mode + Plan mode | Implementation of the core engine. Plan mode forces a research-and-propose step before edits; agent mode executes across files. | `cluttercutter/*.py` — 7 modules, 1,040 lines |
| **C. Testing** | **Claude** as a test-generation agent | Generation of the pytest suite, with explicit instruction to target edge cases rather than happy paths. | `tests/` — 103 tests across 5 files, 861 lines |
| **D. Debugging** | **Claude / Claude Code** | Root-cause analysis of defects, including a logic inversion in the scanner's recursion guard. | Debug session log, captured in commit history |
| **E. CI/QA** | **GitHub Actions** + Claude | Cross-platform test execution and binary builds on real Linux/macOS/Windows runners. | `.github/workflows/build.yml` |

### 2.1 Why this tool combination

The assignment suggests Kiro for test generation, but Kiro's defining
constraint is that it **refuses to write code until a formal specification
exists**. That makes it the natural tool for requirements and design, not for
test generation. We therefore assigned:

- **Kiro → planning** (requirements, design, task breakdown)
- **Cursor → implementation and test generation**

This is a stronger position than the brief suggests, because it produces a
visible artifact: we can open `requirements.md` beside any function and point
at the requirement it implements. The EARS format gives each requirement an
identifier, and our traceability table maps every one to a module and a test.

### 2.2 How AI is integrated without surrendering judgement

The rule we applied: **AI proposes, the team disposes.** Every AI-generated
spec, module and test was reviewed by a human before it was accepted. Three
real examples of AI output being rejected or corrected during development:

1. **Scanner logic inversion.** An AI-generated filter inverted a condition,
   causing non-recursive mode to descend into subfolders. Two existing tests
   caught it immediately. Fixed and re-verified.
2. **Over-confident test expectations.** Several AI-written tests asserted
   behaviour that was wrong (`archive.tar.gz` classified by final suffix;
   reading a file while its byte range was locked). We corrected the
   *tests*, not the code, once we determined the code was right.
3. **CI workflow that passed while doing nothing.** The release job's
   directory guards never matched because `actions/download-artifact` strips
   path prefixes. Every archive step was skipped and the job still exited 0 —
   a green checkmark on an empty release. Found by verifying the actual
   asset count rather than trusting CI status.

The third case is the strongest argument for this project: a tool that
reorganises user files must be verified by observing behavior, not by trusting
a status indicator.

---

## 3. Team Structure (5 Members)

| # | Member | Role | Responsibilities | Primary AI tools |
| --- | --- | --- | --- | --- |
| 1 | *[Name]* | **Team Lead / Spec & Requirements** | Owns `docs/requirements.md` and `docs/design.md`. Runs the Kiro spec workflow, approves each phase, maintains the traceability table. | Kiro |
| 2 | *[Name]* | **Architecture & Core Engine** | Owns `rules.py` and `planner.py`. Designed the purity boundary and the dependency-detection rule. | Cursor |
| 3 | *[Name]* | **Scanner & Safety / Mover** | Owns `scanner.py` and `mover.py`. Implemented hidden-file detection, collision handling, failure isolation, cross-device fallback. | Cursor |
| 4 | *[Name]* | **Test & QA Lead** | Owns `tests/`. Generated and reviewed the suite, defines what counts as sufficient edge-case coverage, maintains the requirement→test mapping. | Claude (test generation) |
| 5 | *[Name]* | **Interfaces, CI & Demo** | Owns `cli.py`, `gui.py`, launchers, installers and the GitHub Actions workflow. Prepares the live demo. | Cursor + Actions |

---

## 4. Success Criteria

| Criterion | Measure | Target |
| --- | --- | --- |
| Functional | Correctly categorised files | ≥ 95% of known types |
| Safety | Zero file deletions in all testing | Absolute |
| Safety | Zero overwrites in all testing | Absolute |
| Safety | Dependency folders never split | Verified by test |
| Testing | Automated coverage | 103 tests, 3 platforms |
| Cross-platform | Windows + Linux + macOS | All tested in CI |
| Usability | No console window on Windows GUI launch | Verified |

---

## 5. Timeline

| Date | Milestone | Deliverable |
| --- | --- | --- |
| Sept 28, 2026 | **Project Proposal** | This document |
| Sept 29 – Oct 4 | Core engine, GUI, CLI, test suite | Working application |
| Oct 5, 2026 | **Mid-Development Checkpoint** | Progress presentation + blocker analysis |
| Oct 6 – 11 | Polish, CI, binary builds, demo prep | Release-ready build |
| Oct 12, 2026 | **Project Presentation** | Live demo + AI-SDLC discussion |

---

## 6. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| AI generates plausible but incorrect code | High | Human review of every artifact; test suite written independently of implementation |
| Data loss | Critical | Dry-run default, no delete path, no overwrite, tests asserting byte-for-byte conservation |
| Demo fails on evaluator's machine | High | Standalone binaries built in CI for all 3 platforms; no Python required |
| Over-reliance on AI | Medium | Document rejected AI outputs; humans own all safety-critical decisions |
| Scope creep | Medium | Explicit out-of-scope list; deferred items documented rather than silently dropped |

---

## Appendix A — Honesty Statement

This project was developed with substantial AI assistance across planning,
implementation and testing. We disclose this explicitly because the tests were
also AI-generated, which makes a passing suite weaker evidence than it
otherwise appears. `AI_DISCLOSURE.md` in the repository records exactly which
tool contributed what, and which claims remain unverified.