# project-scheduler

A desktop project scheduler that computes the **critical path** of a project.

You enter tasks, their durations in working days, and which tasks each one depends on. project-scheduler works out, for every task:

- the earliest and latest start and finish dates;
- the slack, meaning how far the task can slip without delaying the project;
- whether the task is on the critical path.

It also computes the project finish date. It counts only working days, using a calendar of working weekdays and holidays that you can edit.

It enforces its rules: a dependency that would create a cycle is refused, and the cycle is shown. Invalid durations and references to missing tasks are refused as well.

Built with PySide6. It offers a light and a dark theme, and its interface is available in English, German and Japanese. You can switch language while the app runs.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.11 or newer (uv installs it if missing)

No network access, accounts or API keys are needed at runtime.

## Getting started

```bash
git clone <repo-url> project-scheduler
cd project-scheduler
uv sync

# Build the resources and start the app (required once after cloning,
# and after changing .qss, icons or translations):
./build_assets.sh

# Later runs, when nothing needs rebuilding:
uv run project-scheduler
uv run project-scheduler --language de --theme dark   # override the saved choices for this run
```

`build_assets.sh` (a bash script in the project folder) does four things:

1. It runs `pyside6-lupdate` to refresh `translations/*.ts` from the source.
2. It runs `pyside6-lrelease` to compile the `.ts` files to `.qm` files.
3. It runs `pyside6-rcc` to bundle the stylesheets, icons and `.qm` files into `src/project_scheduler/resources_rc.py`.
4. It starts the app. Use `--no-run` to build only. Any other options are passed to the app, for example `./build_assets.sh --language ja`.

From the project folder, run `./build_assets.sh`. The shell only finds scripts by bare name in folders on your `PATH`, so the `./` is required. It works from any directory (give its path), and with `bash`, `sh` or `zsh`.

`project-scheduler` accepts `--language en|de|ja` and `--theme light|dark`. They apply to that run only; the *View* menu changes the saved preference.


## Using it

- **Sample data:** Use *File → Load sample project* and pick a size (100, 1 000 or 5 000 tasks). This shows the app full rather than empty.
- **Editing:** Add, edit and delete tasks in the task table or the task dialog. Every edit can be undone with Ctrl+Z and redone with Ctrl+Shift+Z or Ctrl+Y.
- **Calendar:** Use *Project → Calendar…* to set the working weekdays, the holidays and the project start date.
- **Theme and language:** Both are set from the *View* menu and remembered between runs.

## Scheduling rules

- Durations are whole working days, from 0 to 9 999. A duration of 0 makes the task a milestone.
- Dependencies are finish-to-start: a task starts on the first working day after all of its predecessors finish.
- A task cannot depend on itself, on a task that does not exist, or on anything that would create a cycle.
- If the project start date is not a working day, scheduling begins on the next working day.
- Slack = latest start − earliest start, counted in working days. Tasks with zero slack are critical.

`CLAUDE.md` contains the precise day-counting convention.

## Data files

Projects are saved as JSON (`*.schedule.json`). Each file records a `format_version`.

Files are written atomically: the app writes to a temporary file and then renames it.

If a file is missing, unreadable, from a newer version, or fails validation, the app does not crash. It starts with an empty project, tells you what happened, and keeps a copy of the damaged file next to it as `<name>.corrupt-<timestamp>`.

Settings such as theme, language and recent files are stored with `QSettings`.

## Tests

```bash
./build_assets.sh --no-run             # tests import the compiled resources
uv run pytest tests/
```

- `tests/domain/` tests the scheduling rules and calculations in pure Python, without Qt.
- `tests/storage/` tests saving, loading, versioning and damaged-file recovery.
- `tests/ui/` uses `pytest-qt` to check that every window and dialog opens and responds. It also covers undo/redo, theme switching and language switching.

The UI tests run headless (`QT_QPA_PLATFORM=offscreen` is set in `tests/conftest.py`).

## Project layout

```
src/project_scheduler/
  domain/      pure-Python model, calendar, scheduler, validation (no Qt imports)
  storage/     JSON load/save, format versions, migrations
  samples/     deterministic sample-project generator
  ui/          windows, dialogs, table models, undo commands, theming, i18n
  resources/   resources.qrc, light.qss, dark.qss, icons
translations/  project_scheduler_de.ts, project_scheduler_ja.ts
build_assets.sh  builds translations and resources, then runs the app
tests/         domain/, storage/, ui/
```