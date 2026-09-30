"""Every edit to a running Project is one of these QUndoCommands.

Each command has a ``create`` factory that validates first and returns either the command or a
ValidationError; nothing invalid is ever pushed. ``redo`` and ``undo`` are exact inverses.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QUndoCommand

from ..domain import Task, ValidationError, WorkCalendar
from ..domain.validation import (
    ErrorCode,
    validate_calendar,
    validate_dependency,
    validate_duration,
    validate_name,
    validate_predecessor_set,
)
from .formatting import format_number
from .session import ProjectSession



class AddTaskCommand(QUndoCommand):
    def __init__(self, session: ProjectSession, task: Task) -> None:
        super().__init__(QCoreApplication.translate("Commands", "Add task “{0}”").format(task.name))
        self.session = session
        self.task = task.copy()
        self.previous_next_id = session.project.next_id

    @classmethod
    def create(
        cls, session: ProjectSession, name: str, duration: int, predecessors: Iterable[int] = ()
    ) -> AddTaskCommand | ValidationError:
        preds = list(predecessors)
        error = (
            validate_name(name)
            or validate_duration(duration)
            or validate_predecessor_set(session.project, None, preds)
        )
        if error:
            return error
        task = Task(session.project.next_id, name.strip(), duration, preds)
        return cls(session, task)

    def redo(self) -> None:
        project = self.session.project
        row = len(project.tasks)
        with self.session.inserting_rows(row, row):
            project.tasks.append(self.task.copy())
        project.next_id = self.task.id + 1
        self.session.recompute()

    def undo(self) -> None:
        project = self.session.project
        row = project.row_of(self.task.id)
        with self.session.removing_rows(row, row):
            del project.tasks[row]
        project.next_id = self.previous_next_id
        self.session.recompute()


class EditTaskCommand(QUndoCommand):
    """Changes a task's name and/or duration."""

    def __init__(self, session: ProjectSession, task: Task, name: str, duration: int) -> None:
        super().__init__(QCoreApplication.translate("Commands", "Edit task “{0}”").format(name))
        self.session = session
        self.task_id = task.id
        self.old = (task.name, task.duration)
        self.new = (name, duration)

    @classmethod
    def create(
        cls, session: ProjectSession, task_id: int, name: str | None = None, duration: int | None = None
    ) -> EditTaskCommand | ValidationError | None:
        """Returns None when nothing would change."""
        task = session.project.find(task_id)
        if task is None:
            return ValidationError(ErrorCode.UNKNOWN_TASK, {"task_id": task_id})
        new_name = task.name if name is None else name
        new_duration = task.duration if duration is None else duration
        error = validate_name(new_name) or validate_duration(new_duration)
        if error:
            return error
        new_name = new_name.strip()
        if (new_name, new_duration) == (task.name, task.duration):
            return None
        return cls(session, task, new_name, new_duration)

    def _apply(self, values: tuple[str, int]) -> None:
        task = self.session.project.find(self.task_id)
        task.name, task.duration = values
        self.session.recompute()

    def redo(self) -> None:
        self._apply(self.new)

    def undo(self) -> None:
        self._apply(self.old)


class DeleteTasksCommand(QUndoCommand):
    """Deletes any number of tasks and every dependency that points at them, as one step."""

    def __init__(self, session: ProjectSession, task_ids: set[int]) -> None:
        count = len(task_ids)
        if count == 1:
            text = QCoreApplication.translate("Commands", "Delete task “{0}”").format(session.name_of(next(iter(task_ids))))
        else:
            text = QCoreApplication.translate("Commands", "Delete {0} tasks").format(format_number(count))
        super().__init__(text)
        self.session = session
        project = session.project
        # (row, task) in ascending row order, and the full predecessor lists of surviving tasks
        # that lose an edge, so undo restores them exactly (order included).
        self.removed = [(row, t.copy()) for row, t in enumerate(project.tasks) if t.id in task_ids]
        self.affected = {
            t.id: list(t.predecessors)
            for t in project.tasks
            if t.id not in task_ids and any(p in task_ids for p in t.predecessors)
        }

    @classmethod
    def create(cls, session: ProjectSession, task_ids: Iterable[int]) -> DeleteTasksCommand | ValidationError | None:
        ids = set(task_ids)
        if not ids:
            return None
        existing = session.project.ids()
        missing = sorted(ids - existing)
        if missing:
            return ValidationError(ErrorCode.UNKNOWN_TASK, {"task_id": missing[0]})
        return cls(session, ids)

    def _row_runs(self) -> list[tuple[int, int]]:
        """Contiguous (first, last) row ranges of the removed tasks, ascending."""
        runs: list[tuple[int, int]] = []
        for row, _ in self.removed:
            if runs and runs[-1][1] == row - 1:
                runs[-1] = (runs[-1][0], row)
            else:
                runs.append((row, row))
        return runs

    def redo(self) -> None:
        project = self.session.project
        deleted = {t.id for _, t in self.removed}
        for task_id in self.affected:
            task = project.find(task_id)
            task.predecessors = [p for p in task.predecessors if p not in deleted]
        for first, last in reversed(self._row_runs()):
            with self.session.removing_rows(first, last):
                del project.tasks[first : last + 1]
        self.session.recompute()

    def undo(self) -> None:
        project = self.session.project
        by_row = dict(self.removed)
        for first, last in self._row_runs():
            with self.session.inserting_rows(first, last):
                project.tasks[first:first] = [by_row[r].copy() for r in range(first, last + 1)]
        for task_id, preds in self.affected.items():
            project.find(task_id).predecessors = list(preds)
        self.session.recompute()


class AddDependencyCommand(QUndoCommand):
    def __init__(self, session: ProjectSession, predecessor: int, successor: int) -> None:
        super().__init__(
            QCoreApplication.translate("Commands", "Make “{0}” depend on “{1}”").format(session.name_of(successor), session.name_of(predecessor))
        )
        self.session = session
        self.predecessor = predecessor
        self.successor = successor

    @classmethod
    def create(cls, session: ProjectSession, predecessor: int, successor: int) -> AddDependencyCommand | ValidationError:
        error = validate_dependency(session.project, predecessor, successor)
        return error or cls(session, predecessor, successor)

    def redo(self) -> None:
        self.session.project.find(self.successor).predecessors.append(self.predecessor)
        self.session.recompute()

    def undo(self) -> None:
        preds = self.session.project.find(self.successor).predecessors
        assert preds[-1] == self.predecessor
        preds.pop()
        self.session.recompute()


class RemoveDependencyCommand(QUndoCommand):
    def __init__(self, session: ProjectSession, predecessor: int, successor: int, position: int) -> None:
        super().__init__(
            QCoreApplication.translate("Commands", "Remove dependency of “{0}” on “{1}”").format(
                session.name_of(successor), session.name_of(predecessor)
            )
        )
        self.session = session
        self.predecessor = predecessor
        self.successor = successor
        self.position = position

    @classmethod
    def create(cls, session: ProjectSession, predecessor: int, successor: int) -> RemoveDependencyCommand | ValidationError:
        task = session.project.find(successor)
        if task is None:
            return ValidationError(ErrorCode.UNKNOWN_TASK, {"task_id": successor})
        if predecessor not in task.predecessors:
            return ValidationError(ErrorCode.UNKNOWN_PREDECESSOR, {"task_id": predecessor})
        return cls(session, predecessor, successor, task.predecessors.index(predecessor))

    def redo(self) -> None:
        del self.session.project.find(self.successor).predecessors[self.position]
        self.session.recompute()

    def undo(self) -> None:
        self.session.project.find(self.successor).predecessors.insert(self.position, self.predecessor)
        self.session.recompute()


class _ReplaceCalendarCommand(QUndoCommand):
    def __init__(self, session: ProjectSession, text: str, new: WorkCalendar) -> None:
        super().__init__(text)
        self.session = session
        self.old = session.project.calendar
        self.new = new

    def _apply(self, calendar: WorkCalendar) -> None:
        self.session.project.calendar = calendar
        self.session.recompute()

    def redo(self) -> None:
        self._apply(self.new)

    def undo(self) -> None:
        self._apply(self.old)


class EditCalendarCommand(_ReplaceCalendarCommand):
    """Changes the working weekdays and holidays."""

    @classmethod
    def create(
        cls, session: ProjectSession, working_weekdays: Iterable[int], holidays: Iterable[date]
    ) -> EditCalendarCommand | ValidationError | None:
        weekdays = frozenset(working_weekdays)
        error = validate_calendar(weekdays)
        if error:
            return error
        old = session.project.calendar
        new = WorkCalendar(old.start_date, weekdays, frozenset(holidays))
        if new == old:
            return None
        return cls(session, QCoreApplication.translate("Commands", "Edit calendar"), new)


class ChangeStartDateCommand(_ReplaceCalendarCommand):
    @classmethod
    def create(cls, session: ProjectSession, start_date: date) -> ChangeStartDateCommand | None:
        old = session.project.calendar
        if start_date == old.start_date:
            return None
        return cls(session, QCoreApplication.translate("Commands", "Change start date"), old.with_start_date(start_date))


def predecessor_changes(
    session: ProjectSession, task_id: int, wanted: list[int]
) -> tuple[list[int], list[int]] | ValidationError:
    """Validate a whole new predecessor set; return (to_remove, to_add) edge lists."""
    error = validate_predecessor_set(session.project, task_id, wanted)
    if error:
        return error
    current = session.project.find(task_id).predecessors
    to_remove = [p for p in current if p not in wanted]
    to_add = [p for p in wanted if p not in current]
    return to_remove, to_add
