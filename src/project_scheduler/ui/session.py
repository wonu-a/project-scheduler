"""Holds the window's Project and its current Schedule, and announces changes to views.

Only undo commands (commands.py) call the mutation hooks here.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from PySide6.QtCore import QObject, Signal

from ..domain import Project, Schedule, compute_schedule


class ProjectSession(QObject):
    rowsAboutToBeInserted = Signal(int, int)
    rowsInserted = Signal()
    rowsAboutToBeRemoved = Signal(int, int)
    rowsRemoved = Signal(int, int)
    aboutToReset = Signal()
    reset = Signal()
    scheduleChanged = Signal()

    def __init__(self, project: Project, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.schedule: Schedule = compute_schedule(project)

    def replace_project(self, project: Project) -> None:
        self.aboutToReset.emit()
        self.project = project
        self.schedule = compute_schedule(project)
        self.reset.emit()

    def recompute(self) -> None:
        self.schedule = compute_schedule(self.project)
        self.scheduleChanged.emit()

    def name_of(self, task_id: int) -> str:
        task = self.project.find(task_id)
        return task.name if task else str(task_id)

    @contextmanager
    def inserting_rows(self, first: int, last: int) -> Iterator[None]:
        self.rowsAboutToBeInserted.emit(first, last)
        yield
        self.rowsInserted.emit()

    @contextmanager
    def removing_rows(self, first: int, last: int) -> Iterator[None]:
        self.rowsAboutToBeRemoved.emit(first, last)
        yield
        self.rowsRemoved.emit(first, last)

