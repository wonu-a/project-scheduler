"""Project rules. Every check returns structured errors, never message strings."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .model import MAX_DURATION, Project


class ErrorCode(Enum):
    EMPTY_NAME = "empty_name"
    DURATION_RANGE = "duration_range"
    SELF_DEPENDENCY = "self_dependency"
    UNKNOWN_PREDECESSOR = "unknown_predecessor"
    DUPLICATE_DEPENDENCY = "duplicate_dependency"
    CYCLE = "cycle"
    NO_WORKING_DAYS = "no_working_days"
    INVALID_WEEKDAY = "invalid_weekday"
    UNKNOWN_TASK = "unknown_task"
    DUPLICATE_TASK_ID = "duplicate_task_id"
    INVALID_NEXT_ID = "invalid_next_id"


@dataclass(frozen=True)
class ValidationError:
    code: ErrorCode
    data: Mapping[str, Any] = field(default_factory=dict)


def validate_name(name: str) -> ValidationError | None:
    if not isinstance(name, str) or not name.strip():
        return ValidationError(ErrorCode.EMPTY_NAME)
    return None


def validate_duration(duration: object) -> ValidationError | None:
    if (
        not isinstance(duration, int)
        or isinstance(duration, bool)
        or not 0 <= duration <= MAX_DURATION
    ):
        return ValidationError(
            ErrorCode.DURATION_RANGE, {"value": duration, "min": 0, "max": MAX_DURATION}
        )
    return None


def validate_calendar(working_weekdays: Iterable[int]) -> ValidationError | None:
    weekdays = set(working_weekdays)
    if not weekdays:
        return ValidationError(ErrorCode.NO_WORKING_DAYS)
    bad = sorted(d for d in weekdays if not isinstance(d, int) or not 0 <= d <= 6)
    if bad:
        return ValidationError(ErrorCode.INVALID_WEEKDAY, {"values": tuple(bad)})
    return None


def find_cycle(predecessors: Mapping[int, Iterable[int]]) -> tuple[int, ...] | None:
    """Return one cycle as a path ``(a, b, ..., a)`` in dependency order, or None.

    ``predecessors`` maps every task id to the ids it depends on; all ids must be keys.
    Uses Kahn's algorithm, then walks predecessor links among the leftover nodes.
    """
    preds = {tid: list(p) for tid, p in predecessors.items()}
    indegree = {tid: len(p) for tid, p in preds.items()}
    successors: dict[int, list[int]] = {tid: [] for tid in preds}
    for tid, p in preds.items():
        for pred in p:
            successors[pred].append(tid)

    queue = deque(tid for tid, deg in indegree.items() if deg == 0)
    while queue:
        tid = queue.popleft()
        for succ in successors[tid]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)

    remaining = {tid for tid, deg in indegree.items() if deg > 0}
    if not remaining:
        return None

    # Every leftover node has a predecessor that is also left over; walk back until a repeat.
    node = min(remaining)
    seen: dict[int, int] = {}
    walk: list[int] = []
    while node not in seen:
        seen[node] = len(walk)
        walk.append(node)
        node = next(p for p in preds[node] if p in remaining)
    cycle = walk[seen[node]:]
    cycle.reverse()  # walked against the edges; present in dependency order
    return (*cycle, cycle[0])


def _rotate_to(path: tuple[int, ...], task_id: int) -> tuple[int, ...]:
    body = list(path[:-1])
    if task_id in body:
        i = body.index(task_id)
        body = body[i:] + body[:i]
    return (*body, body[0])


def validate_predecessor_set(
    project: Project, task_id: int | None, predecessors: Iterable[int]
) -> ValidationError | None:
    """Check that ``task_id`` (None for a task not yet added) may have exactly these predecessors."""
    ids = project.ids()
    wanted = list(predecessors)
    if task_id is not None and task_id not in ids:
        return ValidationError(ErrorCode.UNKNOWN_TASK, {"task_id": task_id})
    seen: set[int] = set()
    for pred in wanted:
        if pred == task_id:
            return ValidationError(ErrorCode.SELF_DEPENDENCY, {"task_id": pred})
        if pred not in ids:
            return ValidationError(ErrorCode.UNKNOWN_PREDECESSOR, {"task_id": pred})
        if pred in seen:
            return ValidationError(
                ErrorCode.DUPLICATE_DEPENDENCY, {"predecessor": pred, "successor": task_id}
            )
        seen.add(pred)
    if task_id is None:
        return None  # a brand-new task has no successors, so it cannot close a cycle
    graph = {t.id: t.predecessors for t in project.tasks}
    graph[task_id] = wanted
    cycle = find_cycle(graph)
    if cycle is not None:
        return ValidationError(ErrorCode.CYCLE, {"path": _rotate_to(cycle, task_id)})
    return None


def validate_dependency(project: Project, predecessor: int, successor: int) -> ValidationError | None:
    """Check adding the edge ``predecessor -> successor``."""
    succ = project.find(successor)
    if succ is None:
        return ValidationError(ErrorCode.UNKNOWN_TASK, {"task_id": successor})
    if predecessor in succ.predecessors:
        return ValidationError(
            ErrorCode.DUPLICATE_DEPENDENCY, {"predecessor": predecessor, "successor": successor}
        )
    return validate_predecessor_set(project, successor, [*succ.predecessors, predecessor])


def validate_project(project: Project) -> list[ValidationError]:
    """Full consistency check, used when loading a file."""
    errors: list[ValidationError] = []
    err = validate_calendar(project.calendar.working_weekdays)
    if err:
        errors.append(err)

    ids: set[int] = set()
    for task in project.tasks:
        if task.id in ids:
            errors.append(ValidationError(ErrorCode.DUPLICATE_TASK_ID, {"task_id": task.id}))
        ids.add(task.id)
    if errors:
        return errors
    if ids and project.next_id <= max(ids):
        errors.append(ValidationError(ErrorCode.INVALID_NEXT_ID, {"next_id": project.next_id}))

    for task in project.tasks:
        for e in (validate_name(task.name), validate_duration(task.duration)):
            if e:
                errors.append(ValidationError(e.code, {**e.data, "task_id": task.id}))
        seen: set[int] = set()
        for pred in task.predecessors:
            if pred == task.id:
                errors.append(ValidationError(ErrorCode.SELF_DEPENDENCY, {"task_id": task.id}))
            elif pred not in ids:
                errors.append(ValidationError(ErrorCode.UNKNOWN_PREDECESSOR, {"task_id": pred}))
            elif pred in seen:
                errors.append(
                    ValidationError(
                        ErrorCode.DUPLICATE_DEPENDENCY, {"predecessor": pred, "successor": task.id}
                    )
                )
            seen.add(pred)
    if errors:
        return errors

    cycle = find_cycle({t.id: t.predecessors for t in project.tasks})
    if cycle is not None:
        errors.append(ValidationError(ErrorCode.CYCLE, {"path": cycle}))
    return errors
