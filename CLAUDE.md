# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

project-scheduler is a PySide6 critical-path project scheduler. Read `README.md` for what it does. This file covers how to work on it.

Naming: the repository and the command are `project-scheduler`. The Python package is `project_scheduler`, because Python imports can't contain hyphens. The window title is "Project Scheduler", passed through `tr()`.

When you add or change a feature, follow the workflow in `.claude/skills/scheduler-feature/SKILL.md`.

**Git:** the repository root is the parent `cpsc2710-forai/` directory, which holds other course projects. Keep changes and commits inside `m6-final-project/`.

## Commands

```bash
uv sync                                  # install deps
./build_assets.sh --no-run       # compile translations + Qt resources (run after changing qss/icons/.ts or tr() strings); without --no-run it also starts the app
uv run project-scheduler                 # run the app (options: --language en|de|ja, --theme light|dark)
uv run pytest tests/                     # all tests; must pass before you say you're done
uv run pytest tests/domain -q            # fast loop for scheduling logic
uv run pytest tests/domain/test_scheduler.py::test_name -q   # a single test
```

Tests import the compiled `resources_rc.py`, so run `./build_assets.sh --no-run` before `pytest` after a fresh clone or any asset change. UI tests run headless: `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`.

Never add a runtime network call, account, API key or telemetry.

## Architecture: layers and the rules between them

```
ui  ──►  commands (QUndoCommand)  ──►  domain
 │                                      ▲
 └──────────►  storage  ────────────────┘
```

- **`domain/`** is pure Python and must not import Qt.
  - It uses `datetime.date`, dataclasses and plain collections.
  - It contains the model (`Task`, `Project`, `WorkCalendar`), validation and the scheduler.
  - All scheduling rules live here, and nowhere else.
- **`storage/`** turns a `Project` into JSON and back.
  - It handles `format_version`, migrations, atomic writes and recovery from damaged files.
  - It does not import Qt.
- **`ui/commands.py`** is the only place that mutates a `Project` once the app is running.
  - Every user edit is a `QUndoCommand` pushed onto the window's `QUndoStack`.
- **`ui/`** contains widgets, dialogs, `QAbstractTableModel` subclasses, theming and i18n.
  - Widgets never change domain objects directly.
  - Widgets never compute schedule values themselves.
- **`samples/`** generates deterministic sample projects (100, 1 000 and 5 000 tasks). The performance budget below is measured against the 5 000-task sample.

If you find yourself writing scheduling math in a widget or model, move it into `domain/`.

## Scheduling conventions

These conventions prevent off-by-one bugs. Do not change them without updating the tests and the README.

- **Working-day indices:**
  - Scheduling works on integer working-day indices, not dates.
  - Index 0 is the first working day on or after the project start date.
  - `WorkCalendar` converts in both directions: `index_to_date(i)` and `date_to_index(d)`.
  - `date_to_index` of a non-working day rounds forward to the next working day.
- **What a task occupies:** A task occupies the half-open interval `[ES, EF)`, where `EF = ES + duration`.
- **Forward pass:**
  - `ES = max(EF of predecessors)`, or `0` for a task with no predecessors.
  - The project finish is `max(EF)`.
- **Backward pass:**
  - `LF = min(LS of successors)`, or the project finish for a task with no successors.
  - `LS = LF - duration`.
- **Slack:** `slack = LS - ES`, and a task is critical when `slack == 0`.
- **Displayed dates:**
  - The start date is `index_to_date(ES)`.
  - The finish date is `index_to_date(EF - 1)` when `duration > 0`.
  - A milestone (duration 0) shows a single date, `index_to_date(ES)`.
- **Algorithm:**
  - Use a topological order computed with Kahn's algorithm, which runs in O(V + E).
  - Never recurse over the dependency graph. 5 000-task chains must not hit the recursion limit.
- **Output:** Results come back as an immutable `Schedule` object keyed by task id. Do not store computed values on `Task`.

## Rules the app enforces

Validation lives in `domain/validation.py`. It returns structured errors (an error code plus data) and never message strings. The UI translates the codes into text.

- A task name must not be empty after stripping whitespace.
- A duration must be an integer from 0 to 9 999.
- A task cannot be its own predecessor.
- A predecessor id must refer to an existing task.
- A new dependency must not create a cycle. The error carries the cycle path so the UI can show it.
- The calendar must have at least one working weekday.
- Deleting a task also removes every dependency that points at it, and this happens inside the same undo command.

A command validates its change before it is pushed onto the undo stack. If validation fails, nothing is pushed and the UI shows the error.

**Invariant:** the `Project` held by the window is always valid.

## Undo and redo

- There is one `QUndoCommand` subclass per kind of edit: add task, edit task fields, delete task(s), add dependency, remove dependency, edit calendar, and change the start date.
- `redo()` and `undo()` must be exact inverses. Store what you need to restore in the command, including the removed edges and each task's position in the list.
- A bulk edit, such as deleting 200 selected rows, is a single command or a `beginMacro` block. The user undoes it with one Ctrl+Z.
- Loading a file, loading sample data or creating a new project clears the stack and marks it clean.
- `QUndoStack.cleanChanged` drives the window title asterisk and the unsaved-changes prompt.

## Performance (thousands of records)

- Use `QTableView` with a custom `QAbstractTableModel`. Do not use `QTableWidget` or `QStandardItemModel`.
- `data()` must be O(1).
  - Cache the formatted strings for the current locale.
  - Rebuild the cache when the schedule or the locale changes, not on every paint.
- After an edit, recompute the schedule once, then emit a single `dataChanged` for the affected columns.
- Wrap sample loads and file loads in `beginResetModel` / `endResetModel`.
- Sorting and filtering go through `QSortFilterProxyModel`.
- Budget: loading the 5 000-task sample and scheduling it should take under 1 s. `tests/domain/test_performance.py` guards this with a loose bound.
- If a computation ever exceeds about 100 ms, profile it before reaching for threads.

## Internationalization

- The languages are English (the source language), German (`de`) and Japanese (`ja`).
- Every user-visible string goes through `self.tr()` or `QCoreApplication.translate()`. This includes error messages mapped from validation codes.
  - Never build sentences by concatenating pieces. Use placeholders such as `self.tr("Task {0} depends on itself").format(name)`.
- **Runtime switching:**
  - `ui/i18n.py` removes the old `QTranslator`, installs the new one and sets `QLocale.setDefault(...)`.
  - Every window and dialog handles `QEvent.LanguageChange` in `changeEvent` by calling its `retranslate_ui()`.
  - Table models listen for the locale change, then refresh their cached strings and header data.
- Format numbers and dates only through `QLocale()`: `toString(number)` and `toString(QDate, QLocale.FormatType.ShortFormat)`.
  - Never use f-strings or `strftime` for anything a user sees.
  - The domain returns `datetime.date`, and the conversion to `QDate` happens at the UI boundary.
- **Exemption: sample task names.** The generated sample projects (`samples/generator.py`) name their tasks in English with f-strings, e.g. "Design database 3" or "Milestone 13", in every language. These names are project data saved into files, not interface text, so the translation and formatting rules above don't apply to them. Don't translate them.
- After adding or changing `tr()` strings, run `./build_assets.sh --no-run`, then fill in the `.ts` entries. If you cannot translate an entry well, mark it unfinished rather than guessing silently.

## Styling

- There are two themes, `resources/styles/light.qss` and `dark.qss`, loaded from the Qt resource bundle (`:/styles/...`). Never load them from disk paths.
- Both files share the same selectors. When you style something in one, style it in the other.
- Style by `objectName` and dynamic properties, for example `critical="true"` on rows or badges. Do not hard-code colors in Python.
  - Exception: the table model's `BackgroundRole` / `ForegroundRole` colors come from a small palette object that the theme module updates.
- Use icons from `:/icons/`, in SVG format.
- The goal is a designed look: consistent spacing, a styled header bar, styled table headers and selection, and a clear visual treatment for critical and non-critical tasks. Default grey widgets are a bug.

## Storage

- The file format is JSON:

  ```json
  {"format_version": 1, "project": {...}}
  ```

  The current version constant lives in `storage/format.py`.
- `load()` never raises to the UI. It returns `LoadResult(project, status, message_code, backup_path)`.
  - The status is one of `ok`, `missing`, `corrupt`, `too_new` or `migrated`.
- A corrupt file is renamed to `<name>.corrupt-<YYYYmmdd-HHMMSS>` before the app starts empty.
- `save()` writes to `<name>.tmp` in the same directory, flushes and fsyncs it, then calls `os.replace`.
- **Changing the format:**
  - Bump `format_version`.
  - Add a migration function `migrate_v{n}_to_v{n+1}`.
  - Add a fixture file for the old version under `tests/storage/fixtures/`.

## Tests

- **Domain:** Every rule and every edge case gets a test. Cover at least:
  - an empty project;
  - a single milestone;
  - diamonds, meaning several predecessors and successors;
  - a start date on a weekend;
  - holidays inside a task's span;
  - a cycle of length 1, 2 and n;
  - a 5 000-long chain.
- **Storage:**
  - a round trip;
  - a missing file;
  - invalid JSON;
  - valid JSON with the wrong shape;
  - a `format_version` newer than the app;
  - a migration from every old fixture.
- **UI (pytest-qt):** For each window and dialog:
  - it opens;
  - it accepts input;
  - OK and Cancel behave correctly.
- **Undo:**
  - Each command does `redo → undo → redo` and returns to identical state.
  - A rejected edit pushes nothing onto the stack.
- **i18n:** Switching to `de` changes a menu title, and a date or number cell is re-rendered in German format.
- **Theme:** Switching themes changes the application stylesheet.
- **Test setup:**
  - Use `qtbot.addWidget` so widgets are cleaned up.
  - Prefer `qtbot.waitUntil` over sleeps.
  - Tests must not depend on the host locale. Pin the locale in fixtures.

## Definition of done

1. `uv run pytest tests/` passes.
2. New behavior has tests, and domain behavior has them at the domain level.
3. There are no Qt imports in `domain/` or `storage/`.
4. New strings are wrapped in `tr()`, and the `.ts` files are updated.
5. Both themes cover any new widgets.
6. New edits are undoable.
7. The README is updated if you changed usage, the build steps, the data format or the rules.

## Don'ts

- Don't catch exceptions broadly to make tests pass. Fix the cause.
- Don't add dependencies beyond PySide6, pytest and pytest-qt without a clear reason stated in the PR or commit message.
- Don't use `QTimer` sleeps or `processEvents` loops to hide ordering bugs.