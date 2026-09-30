"""Critical-path scheduling over working-day indices.

A task occupies the half-open interval [ES, EF) with EF = ES + duration.
Forward pass: ES = max(EF of predecessors), or 0. Backward pass: LF = min(LS of successors),
or the project finish. Slack = LS - ES; critical when slack == 0.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

from .calendar import WorkCalendar
from .model import Project


@dataclass(frozen=True)
class TaskTimes:
    duration: int
    es: int
    ef: int
    ls: int
    lf: int

    @property
    def slack(self) -> int:
        return self.ls - self.es

    @property
    def critical(self) -> bool:
        return self.slack == 0


@dataclass(frozen=True)
class Schedule:
    calendar: WorkCalendar
    entries: Mapping[int, TaskTimes]
    order: tuple[int, ...]
    finish_index: int

    def __getitem__(self, task_id: int) -> TaskTimes:
        return self.entries[task_id]

    @property
    def critical_count(self) -> int:
        return sum(1 for t in self.entries.values() if t.critical)

    def start_date(self, task_id: int) -> date:
        return self.calendar.index_to_date(self.entries[task_id].es)

    def finish_date(self, task_id: int) -> date:
        t = self.entries[task_id]
        return self.calendar.index_to_date(t.ef - 1 if t.duration > 0 else t.es)

    def late_start_date(self, task_id: int) -> date:
        return self.calendar.index_to_date(self.entries[task_id].ls)

    def late_finish_date(self, task_id: int) -> date:
        t = self.entries[task_id]
        return self.calendar.index_to_date(t.lf - 1 if t.duration > 0 else t.ls)

    def project_finish_date(self) -> date | None:
        """Date of the last working day of the project; None for an empty project."""
        if not self.entries:
            return None
        return self.calendar.index_to_date(max(self.finish_index - 1, 0))


def compute_schedule(project: Project) -> Schedule:
    """Schedule ``project``, which must be valid (in particular acyclic). O(V + E), no recursion."""
    tasks = {t.id: t for t in project.tasks}
    successors: dict[int, list[int]] = {tid: [] for tid in tasks}
    indegree: dict[int, int] = {}
    for task in project.tasks:
        indegree[task.id] = len(task.predecessors)
        for pred in task.predecessors:
            successors[pred].append(task.id)

    order: list[int] = []
    queue = deque(t.id for t in project.tasks if indegree[t.id] == 0)
    while queue:
        tid = queue.popleft()
        order.append(tid)
        for succ in successors[tid]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                queue.append(succ)
    if len(order) != len(tasks):
        raise ValueError("project contains a dependency cycle")

    es: dict[int, int] = {}
    ef: dict[int, int] = {}
    for tid in order:
        task = tasks[tid]
        start = max((ef[p] for p in task.predecessors), default=0)
        es[tid] = start
        ef[tid] = start + task.duration
    finish = max(ef.values(), default=0)

    ls: dict[int, int] = {}
    lf: dict[int, int] = {}
    for tid in reversed(order):
        late_finish = min((ls[s] for s in successors[tid]), default=finish)
        lf[tid] = late_finish
        ls[tid] = late_finish - tasks[tid].duration

    entries = {
        tid: TaskTimes(tasks[tid].duration, es[tid], ef[tid], ls[tid], lf[tid]) for tid in tasks
    }
    return Schedule(project.calendar, MappingProxyType(entries), tuple(order), finish)
