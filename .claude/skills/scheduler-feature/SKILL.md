---
name: scheduler-feature
description: Step-by-step workflow for adding or changing anything in the project-scheduler PySide6 app. That includes new task fields, scheduling rules, dependency behavior, calendar options, dialogs, table columns, undoable edits, saved-file changes, themes and translations. Use this skill whenever you touch code under src/project_scheduler/ or tests/, even for a "small" UI tweak or a bug fix. Most bugs in this project come from skipping a layer (undo, translation, the second theme, the file format).
---

# Adding a feature to project-scheduler

Every feature crosses several layers. Work through them in this order and skip only the layers that truly do not apply.

`CLAUDE.md` is the authority on conventions. This skill is the checklist for applying them.

## 0. Pin down the behavior first

Before writing code, write two or three sentences on:

- what the user can do;
- what the app computes;
- what rule the app enforces.

Then list the edge cases. For anything touching scheduling, work out one small example by hand using working-day indices, following the conventions in CLAUDE.md, e.g.:

> A (3d) → B (2d), start Fri 2026-01-02, Mon–Fri calendar.
> Index 0 = Fri Jan 2. A: ES 0, EF 3 → Jan 2–Jan 6. B: ES 3, EF 5 → Jan 7–Jan 8.

This hand-worked example becomes your first test.

## 1. Domain (`src/project_scheduler/domain/`)

- Write a failing test in `tests/domain/` from the example in step 0.
- Implement the change in pure Python. Qt imports are not allowed here.
- New invariants go in `validation.py`. Each returns an error code with structured data and never a message string.
- Keep the scheduler O(V + E) and free of recursion.
- Run `uv run pytest tests/domain -q`.

## 2. Storage (`src/project_scheduler/storage/`) — only if the saved data changes

- Bump `FORMAT_VERSION` and add `migrate_v{n}_to_v{n+1}`.
- Add an old-version fixture and a migration test.
- Make sure a damaged or unexpected value in the new field produces a `corrupt` status, never an exception.

## 3. Undo command (`src/project_scheduler/ui/commands.py`) — if the user can edit it

- Validate in the command's constructor, or in a factory, before pushing it onto the stack. If the change is invalid, return the error and push nothing.
- Store everything `undo()` needs to restore the exact previous state, including side effects such as removed dependencies and list positions.
- Write a test: `redo → undo → redo` returns to identical project state and an identical schedule.
- Group bulk actions into a single undoable step.

## 4. Table model and views (`src/project_scheduler/ui/`)

- If you add a column, update:
  - the column enum;
  - `headerData` (translated);
  - `data` for `DisplayRole` and `SortRole`;
  - the cached formatted strings.
- Format dates and numbers only through `QLocale()`.
- Emit one `dataChanged` or reset per edit. Never emit one signal per cell in a loop.
- Style state with dynamic properties or theme palette roles, not with hard-coded colors.

## 5. Dialogs and widgets

- Every visible string goes through `self.tr(...)`. Use placeholders, not concatenation.
- Implement `retranslate_ui()` and call it from `changeEvent` on `QEvent.LanguageChange`.
- Give widgets `objectName`s the QSS can target.
- Show validation errors inline, mapped from error codes to translated text.

## 6. Themes (`src/project_scheduler/resources/styles/`)

- Add the selectors to **both** `light.qss` and `dark.qss`.
- Look at the result in both themes. A widget that looks default grey means the styling is unfinished.

## 7. Translations

- Run `./build_assets.sh --no-run` to refresh the `.ts` files and rebuild the resources.
- Fill in the German and Japanese entries in `translations/`. Mark any entry you're unsure of as unfinished, and say so in your summary.
- Re-run the build so the new `.qm` files are bundled.

## 8. UI tests (`tests/ui/`, pytest-qt)

- Any new dialog: it opens, it accepts input, OK applies the change (and pushes a command), and Cancel changes nothing.
- A new column or new formatting: switch the locale to `de` and assert that the cell text changes format.
- Undo through the UI: trigger the action, press Ctrl+Z, assert the previous state.

## 9. Finish

- Run `uv run pytest tests/`. It must pass completely.
- Launch `uv run project-scheduler` and load the 5 000-task sample. Check that the app stays responsive after your change.
- Update the README if you changed usage, the rules, the data format or the build steps.
- Summarize for the user:
  - what changed;
  - which rules are enforced;
  - which tests you added;
  - anything left unfinished, such as uncertain translations.

## Common traps

- A finish date that is one day late means you displayed `EF` instead of `EF - 1`.
- Deleting a task without removing the dependencies that point at it leaves the project invalid, and undo will not restore those dependencies.
- The language changes but the table cells don't: the model's string cache was not rebuilt on the locale change.
- Tests pass on your machine but fail elsewhere: the host locale leaked in, so pin it in the fixture.
- A `RecursionError` on the large sample means someone wrote a recursive depth-first search. Use Kahn's algorithm.