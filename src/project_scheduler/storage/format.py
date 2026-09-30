"""The on-disk document shape: ``{"format_version": N, "project": {...}}``.

Changing the format: bump FORMAT_VERSION, add ``migrate_v{n}_to_v{n+1}`` to MIGRATIONS and add a
fixture for the old version under tests/storage/fixtures/.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from ..domain import Project, Task, WorkCalendar

FORMAT_VERSION = 1

# Maps version n to the function converting a version-n document into version n+1.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


class FormatError(ValueError):
    """The document does not have the expected shape."""


def migrate(document: dict[str, Any], from_version: int) -> dict[str, Any]:
    for version in range(from_version, FORMAT_VERSION):
        step = MIGRATIONS.get(version)
        if step is None:
            raise FormatError(f"no migration from format version {version}")
        document = step(document)
        document["format_version"] = version + 1
    return document


def document_from_project(project: Project) -> dict[str, Any]:
    cal = project.calendar
    return {
        "format_version": FORMAT_VERSION,
        "project": {
            "start_date": cal.start_date.isoformat(),
            "calendar": {
                "working_weekdays": sorted(cal.working_weekdays),
                "holidays": sorted(h.isoformat() for h in cal.holidays),
            },
            "next_id": project.next_id,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "duration": t.duration,
                    "predecessors": list(t.predecessors),
                }
                for t in project.tasks
            ],
        },
    }


def _expect(value: Any, kind: type, what: str) -> Any:
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise FormatError(f"{what} must be {kind.__name__}")
    return value


def _date(value: Any, what: str) -> date:
    try:
        return date.fromisoformat(_expect(value, str, what))
    except ValueError as exc:
        raise FormatError(f"{what} is not an ISO date") from exc


def project_from_document(document: dict[str, Any]) -> Project:
    """Build a Project from a current-version document. Raises FormatError on a wrong shape."""
    data = _expect(document.get("project"), dict, "project")
    start = _date(data.get("start_date"), "start_date")
    cal = _expect(data.get("calendar"), dict, "calendar")
    weekdays = [_expect(d, int, "working weekday") for d in _expect(cal.get("working_weekdays"), list, "working_weekdays")]
    if not weekdays or any(not 0 <= d <= 6 for d in weekdays):
        raise FormatError("working_weekdays must be non-empty weekday numbers 0-6")
    holidays = [_date(h, "holiday") for h in _expect(cal.get("holidays"), list, "holidays")]
    tasks = []
    for raw in _expect(data.get("tasks"), list, "tasks"):
        raw = _expect(raw, dict, "task")
        preds = [_expect(p, int, "predecessor") for p in _expect(raw.get("predecessors"), list, "predecessors")]
        tasks.append(
            Task(
                id=_expect(raw.get("id"), int, "task id"),
                name=_expect(raw.get("name"), str, "task name"),
                duration=_expect(raw.get("duration"), int, "duration"),
                predecessors=preds,
            )
        )
    next_id = _expect(data.get("next_id"), int, "next_id")
    return Project(
        calendar=WorkCalendar(start, frozenset(weekdays), frozenset(holidays)),
        tasks=tasks,
        next_id=next_id,
    )
