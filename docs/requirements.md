# Requirements — ClutterCutter

Format: EARS notation (Easy Approach to Requirements Syntax).
Each requirement is traceable to the code that implements it and the test
that proves it.

## Glossary

| Term | Meaning |
| --- | --- |
| **Target folder** | The single folder the user explicitly names. Nothing outside it is ever touched. |
| **Dry run** | The default mode. Computes and displays the plan; changes nothing on disk. |
| **Apply** | The mode that actually moves files. Must be requested explicitly. |
| **Protected** | A file whose type cannot be confidently identified. Never moved unless the user opts in. |
| **Plan** | The ordered list of (source, destination) moves, computed without disk writes. |

## Functional requirements

### R1 — Scanning

**R1.1** WHEN the user requests a scan of a valid target folder, THEN
ClutterCutter SHALL enumerate every regular file in that folder.

**R1.2** WHEN a file is hidden or marked system by the operating system, THEN
ClutterCutter SHALL exclude it from the plan AND record it as skipped.

**R1.3** WHEN `--recursive` is not specified, THEN ClutterCutter SHALL NOT
descend into subdirectories.

**R1.4** WHEN a file cannot be read due to permissions, THEN ClutterCutter
SHALL record it as skipped and CONTINUE scanning rather than aborting.

**R1.5** WHEN an entry is not a regular file (directory, socket, device), THEN
ClutterCutter SHALL skip it.

### R2 — Classification

**R2.1** WHEN a file's extension matches a known category, THEN ClutterCutter
SHALL assign that category.

**R2.2** WHEN the file's extension is unknown, THEN ClutterCutter SHALL assign
the Protected category and SHALL NOT guess.

**R2.3** WHEN an extension differs only by case, THEN ClutterCutter SHALL
classify it identically to the lowercase form.

**R2.4** WHEN a file has no extension, THEN ClutterCutter SHALL assign
Protected.

### R3 — Planning

**R3.1** WHEN a plan is built, THEN ClutterCutter SHALL NOT modify the
filesystem in any way.

**R3.2** WHEN a destination filename already exists, THEN ClutterCutter SHALL
generate a non-conflicting name of the form `name (n).ext` and SHALL NOT
overwrite.

**R3.3** WHEN two or more source files would resolve to the same destination,
THEN ClutterCutter SHALL assign each a distinct destination.

**R3.4** WHEN constructing any destination, THEN ClutterCutter SHALL verify the
destination is a descendant of the target folder and reject it otherwise.

### R4 — Safety (the controlling requirements)

**R4.1** WHEN no `--apply` flag is supplied, THEN ClutterCutter SHALL execute a
dry run and SHALL NOT create directories or move files.

**R4.2** WHEN a dry run completes, THEN ClutterCutter SHALL report every move
it would perform.

**R4.3** WHEN a file is classified Protected, THEN ClutterCutter SHALL leave it
in place UNLESS the user supplied `--include-protected`.

**R4.4** ClutterCutter SHALL NEVER delete a file.

**R4.5** ClutterCutter SHALL NEVER overwrite an existing file.

**R4.6** WHEN a move fails, THEN ClutterCutter SHALL record the failure and
CONTINUE with the remaining files.

**R4.7** WHEN `--apply` is used without `--yes`, THEN ClutterCutter SHALL
require explicit user confirmation before moving anything.

### R5 — Cross-device behaviour

**R5.1** WHEN a move fails because source and destination are on different
filesystems, THEN ClutterCutter SHALL copy the file and then remove the source,
preserving content and modification time.

### R6 — Interfaces

**R6.1** ClutterCutter SHALL provide a command-line interface.

**R6.2** ClutterCutter SHALL provide a graphical interface built on the same
core engine as the CLI.

**R6.3** WHEN the GUI has not yet produced a non-empty plan, THEN the Apply
control SHALL be disabled.

**R6.4** WHEN the user requests Apply in the GUI, THEN ClutterCutter SHALL
prompt for confirmation first.

**R6.5** WHEN `--json` is specified, THEN ClutterCutter SHALL emit the plan as
valid JSON to stdout.

## Non-functional requirements

**N1** A scan of 10,000 files SHALL complete within 5 seconds on a typical
developer machine.

**N2** The engine SHALL be platform-independent: identical behaviour on
Windows and Linux, with hidden-file detection adapting to each OS's mechanism.

**N3** No third-party runtime dependencies. Standard library only.

**N4** The core engine SHALL be testable without a display server.

## Traceability

| Requirement | Module | Test |
| --- | --- | --- |
| R1.2 | scanner.is_hidden_or_system | `test_scanner.py::test_hidden_files_are_excluded` |
| R1.4 | scanner.scan | `test_scanner.py::test_windows_hidden_attribute_is_respected` |
| R2.2 | rules.categorise | `test_scanner.py::test_unclassified_is_protected` |
| R3.1 | planner.build_plan | `test_planner.py::test_build_plan_is_pure` |
| R3.2 | planner.unique_destination | `test_planner.py::test_existing_destination_gets_numbered_rename` |
| R3.4 | planner.build_plan | `test_planner.py::test_no_destination_escapes_root` |
| R4.1 | cli.main | `test_cli.py::test_no_flags_changes_nothing` |
| R4.3 | planner.build_plan | `test_mover.py::test_protected_stay_put` |
| R4.4 | mover.apply_plan | `test_mover.py::test_no_files_are_deleted` |
| R4.5 | mover.apply_plan | `test_mover.py::test_existing_destination_is_never_replaced` |
| R4.6 | mover.apply_plan | `test_mover.py::test_one_locked_file_does_not_abort_the_run` |
| R5.1 | mover.apply_plan | `test_mover.py::test_exdev_falls_back_to_copy_then_remove` |