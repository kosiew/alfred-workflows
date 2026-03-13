# AGENTS.md

## Purpose

This repository contains small Alfred workflow entrypoints plus the Python and JavaScript helpers they invoke.

## Key Entry Points

- `a_process_text.py` contains the primary implementation for the text-processing workflow.
- `a_weekly_note.py` contains the primary implementation for the weekly-note workflow.
- `process_text.py` is a thin wrapper used by Alfred. It adds this repository to `sys.path`, imports `a_process_text`, and calls `a_process_text.do()`.
- `weekly_note.py` is a thin wrapper used by Alfred. It adds this repository to `sys.path`, imports `a_weekly_note`, and calls `a_weekly_note.do()`.
- `ghs.py`, `journal.py`, `quick_navigate.py`, and related helpers are standalone workflow scripts.
- `workflows/` contains Alfred workflow assets such as shell entrypoints.

## Working Conventions

- When changing workflow behavior for process text or weekly note, edit `a_process_text.py` or `a_weekly_note.py` rather than the wrapper files unless the Alfred bootstrap behavior itself needs to change.
- Keep wrapper scripts minimal. They exist to redirect Alfred into the real implementation files.
- Tests live at the repository root as `test_*.py` files.
- Shared parsing and import-manipulation helpers live in files such as `python_import_helpers.py` and `rust_import_helpers.py`.

## Practical Notes

- Some scripts reference absolute local paths for external tools and source directories. Preserve that behavior unless you are intentionally changing local-environment assumptions.
- Prefer small, targeted edits. This repository is mostly a collection of utility scripts rather than a single packaged application.