# Tasks — ClutterCutter

Derived from `requirements.md`. Each task lists the requirements it satisfies
and the tests that verify it.

## Phase 1 — Core engine

- [x] **T1.1** Define the category table and `categorise()`
  - Reqs: R2.1, R2.2, R2.4
  - Tests: `test_scanner.py::TestCategorise`

- [x] **T1.2** Implement hidden/system detection for both platforms
  - Reqs: R1.2, N2
  - Tests: `test_hidden_files_are_excluded`,
    `test_windows_hidden_attribute_is_respected`,
    `test_posix_symlinks` (POSIX)

- [x] **T1.3** Implement the scanner
  - Reqs: R1.1, R1.3, R1.4, R1.5
  - Tests: `test_scanner.py::TestScan`

## Phase 2 — Planning

- [x] **T2.1** Implement `build_plan()` as a pure function
  - Reqs: R3.1, R3.4, R4.3
  - Tests: `test_build_plan_is_pure`, `test_no_destination_escapes_root`,
    `test_protected_left_alone_by_default`

- [x] **T2.2** Implement collision-safe naming, case-insensitively
  - Reqs: R3.2, R3.3
  - Tests: `test_existing_destination_gets_numbered_rename`,
    `test_two_sources_one_name_resolve_distinctly`,
    `test_case_variant_conflict_detected`

## Phase 3 — Execution

- [x] **T3.1** Implement `apply_plan()` with per-file failure isolation
  - Reqs: R4.6, N2
  - Tests: `test_one_locked_file_does_not_abort_the_run`,
    `test_vanished_source_is_reported_not_raised`

- [x] **T3.2** Guarantee no deletion and no overwrite
  - Reqs: R4.4, R4.5
  - Tests: `test_no_files_are_deleted`,
    `test_existing_destination_is_never_replaced`

- [x] **T3.3** Handle the cross-device fallback
  - Reqs: R5.1
  - Tests: `test_exdev_falls_back_to_copy_then_remove`

## Phase 4 — Interfaces

- [x] **T4.1** CLI with dry-run as the default
  - Reqs: R4.1, R4.2, R4.7, R6.1, R6.5
  - Tests: `test_cli.py::TestDryRunDefault`, `TestApply`, `TestJsonOutput`

- [x] **T4.2** Tkinter GUI over the same engine
  - Reqs: R6.2, R6.3, R6.4
  - Manual verification: Apply disabled until a non-empty plan exists

- [x] **T4.3** Launchers for Windows and Linux
  - Reqs: R6.1, R6.2
  - Files: `ClutterCutter.bat`, `cc-cli.bat`, `cluttercutter.sh`,
    `cluttercutter-cli.sh`, `Desktop/ClutterCutter.bat`

## Deferred

- [ ] **T5.1** Undo — log every applied move to a journal so a run can be
      reversed. Not required by any current requirement; the absence of
      deletion makes this lower priority.
- [ ] **T5.2** Content-based classification (magic bytes) for files with
      missing or misleading extensions. Would reduce the Protected category.
- [ ] **T5.3** Configuration file for category overrides.
- [ ] **T5.4** Performance measurement against N1 (10,000 files / 5s).