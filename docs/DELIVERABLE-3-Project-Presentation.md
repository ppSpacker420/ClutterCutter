# Deliverable 3 — Project Presentation

**Project:** ClutterCutter — Automated Local Storage Manager
**Group size:** 5
**Due:** October 12, 2026
**Repository:** https://github.com/ppSpacker420/ClutterCutter
**Release:** https://github.com/ppSpacker420/ClutterCutter/releases/tag/v1.0.0

---

## 1. Presentation Agenda (20 minutes)

| # | Section | Time | Presenter |
| --- | --- | --- | --- |
| 1 | Problem and solution | 2 min | Member 1 |
| 2 | **Live demonstration** | 8 min | Member 5 |
| 3 | Architecture and safety design | 3 min | Member 2 |
| 4 | **AI in planning** (Kiro) | 2 min | Member 1 |
| 5 | **AI in development** (Cursor) | 2 min | Members 2 & 3 |
| 6 | **AI in testing** (Claude) | 2 min | Member 4 |
| 7 | What AI got wrong | 1 min | Member 4 |

---

## 2. Live Demonstration Script

### 2.1 Setup before the presentation

Prepare a disposable test folder (`demo/`) containing:

```
demo/
  holiday.jpg            loose file
  screenshot.png         loose file
  clip.mp4               loose file
  song.mp3               loose file
  report.pdf             loose file
  mystery.qqq            unclassifiable
  noextension            unclassifiable
  mysite/                <- web page, must NOT be split
    index.html
    style.css
    app.js
    logo.png
  myproject/             <- Python project, must NOT be split
    requirements.txt
    main.py
    config.yaml
```

This fixture is chosen because it demonstrates **three distinct behaviours in
one scan**: normal sorting, refusal to classify, and refusal to split a
dependency folder.

### 2.2 Demonstration steps

**Step 1 — Launch (30 sec)**
Double-click `ClutterCutter.bat`.
> *Note the absence of a terminal window. The launcher uses `pythonw.exe`,
> Python's console-less build, so the GUI is not attached to a shell.*

**Step 2 — Scan (1 min)**
Select the folder, press **Scan**.

Point out the two panels:
- **Preview** — 7 files proposed for sorting, with destination shown per row
- **Left alone** — 2 files, with reasons

> *Point at the Apply button: it is disabled. Nothing can move until a scan
> has produced a plan.*

**Step 3 — Explain before applying (1 min)**
> *Two files stayed behind. `mystery.qqq` and `noextension` have extensions we
> don't recognise, so we won't guess. They go to a `Protected` category and
> don't move unless I explicitly allow it. We'd rather leave a file alone than
> put it in the wrong place.*

**Step 4 — Apply (1 min)**
Press **Apply moves**. Read the confirmation dialog aloud, then approve.
Show the resulting folder tree:

```
Documents/  Images/  Audio/  Video/  Documents/
mystery.qqq          <- still at the top level
noextension          <- still at the top level
mysite/  myproject/  <- completely untouched
```

**Step 5 — The safety demonstrations (3 min)**

| Action | Expected result | Why it matters |
| --- | --- | --- |
| Run Scan again | "Nothing to move" | Idempotent — no churn on repeat runs |
| Look inside `mysite/` | All 4 files present | The HTML still has its CSS, JS and image |
| Look inside `myproject/` | All 3 files present | `requirements.txt` still beside `main.py` |

> *This is the part I'd most like you to remember. A naive version of this
> tool sorts by file extension. It would have moved `main.py` to a Code
> folder and `requirements.txt` to a Documents folder — and `pip install -r`
> would break with no error message telling you why. We built folder-level
> dependency detection so that a folder containing a project marker, or any
> web page, is treated as one indivisible unit.*

**Step 6 — CLI demo (1 min)**
```bash
cc-cli.bat "C:\Users\...\demo"
```
> *Same engine underneath. The CLI isn't a separate implementation — it's the
> same three functions the GUI calls, so there's no way for them to disagree.*
>
> *Notice the last line: "DRY RUN - nothing was changed." You have to type
> `--apply` to move anything.*

**Step 7 — The one-line safety argument (30 sec)**
> *Five properties, each in code, each with a test: dry-run is the default;
> nothing is deleted; nothing is overwritten; unidentifiable files are left
> alone; dependency folders are never split.*
>
> *And one design decision I'd argue for: dry-run is the**absence** of a flag
> rather than a flag you can forget. There's no way to move files by omitting
> something.*

---

## 3. AI Integration — Planning (Kiro)

### 3.1 What Kiro did

Kiro is AWS's spec-driven agentic IDE. Its defining constraint is that it will
not generate code until a formal specification exists. It produces three
documents in sequence, each requiring human approval before the next:

1. `requirements.md` — user stories and acceptance criteria in **EARS
   notation**, the format developed for aerospace and safety-critical systems
2. `design.md` — architecture, component boundaries, data models
3. `tasks.md` — sequenced, requirement-mapped implementation steps

### 3.2 Why we assigned Kiro here rather than to testing

The assignment suggested Kiro for test generation. Because Kiro's entire
premise is that code generation is gated on a completed specification, using it
to write tests would have meant either skipping the spec phase or generating
tests against an unwritten contract. We reassigned it to planning, where its
constraint becomes an advantage.

### 3.3 The artifact an evaluator can inspect

We can open `docs/requirements.md` beside any function in the codebase. Each
requirement has an identifier, and the traceability table maps it to the module
that implements it and the test that verifies it:

| Requirement | Module | Test |
| --- | --- | --- |
| R4.1 — dry-run default | `cli.main` | `test_no_flags_changes_nothing` |
| R4.4 — no deletion | `mover.apply_plan` | `test_no_files_are_deleted` |
| R4.5 — no overwrite | `mover.apply_plan` | `test_existing_destination_is_never_replaced` |
| R4.6 — failure isolation | `mover.apply_plan` | `test_one_locked_file_does_not_abort_the_run` |
| R5.1 — cross-device | `mover.apply_plan` | `test_exdev_falls_back_to_copy_then_remove` |

Twenty requirements, each with this triple. This is the artifact that makes
the AI-SDLC claim checkable rather than asserted.

### 3.4 Human input

We did not accept Kiro's output uncritically. Two requirements were rewritten
because the generated version was unachievable or unsafe as written — for
example, an initial draft did not distinguish dry-run from apply, which would
have made the safety claim unenforceable.

---

## 4. AI Integration — Development (Cursor)

### 4.1 How we used it

Cursor's **Plan mode** was the primary tool. It forces a research-and-propose
step: search the codebase, ask clarifying questions, produce a plan with file
references, and **wait for approval** before writing anything. Agent mode then
executed the approved plan.

We avoided the failure mode Cursor's docs warn about — "different models
respond very differently to prompts" — by writing explicit prompts and giving
the agent verifiable goals rather than open-ended instructions.

### 4.2 The architectural decision AI produced

The pipeline shape came out of this process:

```
scanner --> planner --> mover
 (reads)    (pure)     (writes, only with --apply)
```

The scanner and planner **never write to disk**. This is what makes the
preview trustworthy: the preview and the execution are generated by the same
function, so they cannot drift apart. We rejected the alternative — computing a
separate preview projection — because it would be a second source of truth.

### 4.3 Bugs AI produced, and how we caught them

**Logic inversion in the recursion guard.** A generated filter was inverted,
causing non-recursive mode to descend into subfolders. Two pre-existing tests
failed immediately. Notably, the tests that caught it were written *before* the
bug existed.

**A portability defect visible on only one platform.** Collision detection used
`Path.exists()`, which is case-sensitive on Linux but case-insensitive on
Windows. On Windows, `report.pdf` and `REPORT.PDF` are the same file, so the
conflict would have gone undetected — the tool could have overwritten a file on
one platform but not the other. Now case-folded comparison runs on both.

---

## 5. AI Integration — Testing (Claude)

### 5.1 Approach

The suite was generated with explicit instruction to target edge cases rather
than happy paths, and to avoid mocking. The prompt specified the failure modes
we cared about: locked files, name collisions, case-insensitive filesystems,
cross-device moves, permission denial, and hidden-file mechanisms on two
operating systems.

### 5.2 Result

**103 tests, 861 lines**, against 1,040 lines of source.

Coverage is deliberately weighted toward failure modes. Examples:

| Test | What it proves |
| --- | --- |
| `test_no_files_are_deleted` | Byte count conserved exactly across a run |
| `test_one_locked_file_does_not_abort_the_run` | One locked file doesn't stop the others |
| `test_exdev_falls_back_to_copy_then_remove` | Cross-device move preserves content |
| `test_case_variant_conflict_detected` | Windows filename semantics respected on all platforms |
| `test_html_and_its_assets_stay_together` | Dependency folders are never split |
| `test_project_in_downloads_survives_a_run` | Loose files sorted, project untouched |

### 5.3 Verification across platforms

The suite runs on real runners, not just locally:

| Runner | Result |
| --- | --- |
| `ubuntu-latest` | 100 passed, 3 skipped |
| `windows-latest` | 102 passed, 1 skipped |
| `macos-latest` | 100 passed, 3 skipped |

The differing skip counts are meaningful: Windows-only tests (hidden file
attributes) skip on Unix, and the POSIX symlink test skips on Windows. This
confirms platform-specific code paths are genuinely exercised.

### 5.4 The honest limitation

**The tests were written by the same AI system that wrote the code.** A
passing suite generated alongside the implementation is weaker evidence of
correctness than an independently written one, and we do not claim otherwise.

Three generated tests were simply wrong — they encoded a misreading of the
specification rather than a real defect. In each case we corrected the test,
after independently establishing that the code was right. The lesson is worth
stating plainly: **an AI-written test is not an independent check on
AI-written code.** Human review remains the control that makes this safe.

---

## 6. What AI Got Wrong (1 minute)

We think this section is more interesting than the successes.

**A CI pipeline that passed while doing nothing.** Our first published release
attached zero binaries while every job showed a green checkmark. The archive
step's directory guards never matched because `actions/download-artifact`
strips path prefixes, and the step ended with `|| true`, swallowing the failure.
We found it by checking the actual asset count. *For a tool that moves people's
files, a CI status is not evidence.*

**Tests that confidently encoded a misreading.** An AI-generated test expected
`archive.tar.gz` to be unclassified, when classifying by final suffix is
correct. Another read a file while holding an exclusive lock, so the assertion
itself threw. Both looked authoritative and were both wrong.

**A generated filter with an inverted condition.** Non-recursive scanning
descended into subfolders. Caught by two tests that predated the bug.

Our working rule throughout: **AI proposes, the team disposes.** Every
specification, module and test was reviewed by a human before acceptance. The
safety-critical decisions — dry-run polarity, no-overwrite, dependency
detection — were all made by us, not generated.

---

## 7. Closing

### 7.1 What we'd build next

| Item | Rationale |
| --- | --- |
| Undo journal | Log every applied move so a run can be reversed |
| Content-based classification | Magic-byte sniffing would reduce the Protected category |
| Configurable categories | A user-facing rules file |
| Larger-file benchmarking | Current figures use 64-byte files; real large-file I/O is unmeasured |

### 7.2 Closing statement

> *ClutterCutter is a small tool with an unremarkable feature set — sorting
> files by type. The interesting part is what it refuses to do.*
>
> *It won't move anything you didn't ask it to. It won't delete. It won't
> overwrite. It won't guess at a file it doesn't understand. And it won't pull
> your project apart because it happened to be sitting in the same folder.*
>
> *Every one of those decisions is a line of code and a test. That's the
> standard we'd want anyone to hold this project to.*

---

## Appendix A — Honest Disclosure

This project was built with substantial AI assistance across all three phases.
`AI_DISCLOSURE.md` in the repository records which tool contributed what, and
specifically names that:

1. The tests were AI-generated and are therefore not independent verification
2. Linux support is CI-verified on Ubuntu only; Fedora, Arch and openSUSE are
   untested
3. Cross-device moves are verified by fault injection, not real hardware
4. The 10,000-file performance target is **measured and met** (2.84s against a
   5s budget), but with 64-byte test files. Large-file I/O is unmeasured.

We have stated these because a presentation that only lists successes is less
useful to an evaluator than one that shows where our verification stopped.

## Appendix B — Team Roles

| Member | Role | Presentation segment |
| --- | --- | --- |
| 1 | Team Lead / Spec & Requirements | Problem & solution; AI in planning |
| 2 | Architecture & Core Engine | Architecture & safety design; AI in development |
| 3 | Scanner & Safety / Mover | Safety demonstration; AI in development |
| 4 | Test & QA Lead | AI in testing; What AI got wrong |
| 5 | Interfaces, CI & Demo | Live demonstration |

## Appendix C — Demo Checklist

- [ ] Test folder prepared (see 2.1)
- [ ] GUI launcher tested on the presentation machine
- [ ] Standalone `.exe` downloaded as backup — no Python required
- [ ] Fallback: screen recording of the demo
- [ ] `docs/requirements.md` open in an editor for the traceability walkthrough
- [ ] Confirm the terminal is closed before presenting (no console window)