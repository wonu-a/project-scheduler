"""The editable project model. Computed schedule values never live here."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from .calendar import WorkCalendar

MAX_DURATION = 9999


@dataclass
class Task:
    id: int
    name: str
    duration: int
    predecessors: list[int] = field(default_factory=list)
    notes: str = ""  # free text; never affects scheduling

    def copy(self) -> Task:
        return replace(self, predecessors=list(self.predecessors))


@dataclass
class Project:
    calendar: WorkCalendar
    tasks: list[Task] = field(default_factory=list)
    next_id: int = 1

    @classmethod
    def new(cls, start_date: date) -> Project:
        return cls(calendar=WorkCalendar(start_date))

    def find(self, task_id: int) -> Task | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def row_of(self, task_id: int) -> int:
        for row, task in enumerate(self.tasks):
            if task.id == task_id:
                return row
        raise KeyError(task_id)

    def ids(self) -> set[int]:
        return {t.id for t in self.tasks}
