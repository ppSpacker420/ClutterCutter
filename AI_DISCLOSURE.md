# AI Assistance Disclosure

**This project was developed with AI assistance.** Please read this before
using, reviewing, or teaching it.

## What AI was used for

ClutterCutter is a solo student project built with heavy AI assistance across
the whole software development lifecycle. Specifically:

| Stage | Tool | Contribution |
| --- | --- | --- |
| Specification | Kiro (AWS) | Structured the requirements in `docs/requirements.md` using EARS notation, and the design decisions in `docs/design.md` |
| Implementation | Cursor / Claude Code | Wrote and refactored the Python source, including the scanner, planner, and mover |
| Test generation | Claude Code | Generated the pytest suite in `tests/`, including edge cases such as locked files, name collisions, and cross-device moves |
| Debugging | Claude Code | Identified and fixed a logic inversion in the scanner's recursion guard |
| Documentation | Claude Code | Wrote the README and the spec documents |

Every line of code in this repository was produced or reviewed with AI
assistance. The project is a demonstration of AI-assisted development, not a
claim of unassisted authorship.

## Why this file exists

There is growing evidence that AI-generated code looks convincing while
containing real defects. Two specific things a reader should know:

1. **The tests were also written by AI.** A passing test suite written by the
   same system that wrote the code is weaker evidence of correctness than it
   appears. Treat the suite as a starting point, not proof.

2. **The Linux support is tested only on Ubuntu.** CI runs the full suite on
   `ubuntu-latest`, and the launchers and GUI are exercised on a virtual
   display. Fedora, Arch and openSUSE are **not** tested, and the tkinter
   package names differ between them. macOS passes the test suite but the
   launchers are not exercised there. See the "Verification status" section
   of the README.

## Safety-critical properties

ClutterCutter moves and reorganises real files on a user's disk. Four
properties are enforced in code and covered by tests, and are worth auditing
before you trust this with anything you care about:

- **Dry-run is the default.** No file moves without an explicit `--apply`.
- **Nothing is deleted.** There is no code path that removes a user file.
- **Nothing is overwritten.** Collisions are resolved by renaming the incoming
  file.
- **Dependency-aware.** A folder that looks like a working unit (a project, a
  web page, a virtual environment) is treated as atomic and left untouched.

These are claims, not proofs. Verify them against your own requirements before
pointing the tool at anything irreplaceable, and test on a copy first.

## License

MIT — see `LICENSE`. The code is provided as-is with no warranty.