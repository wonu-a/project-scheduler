"""Deterministic sample projects, so the app can be shown full rather than empty."""

from __future__ import annotations

import random
from datetime import date

from ..domain import Project, Task, WorkCalendar

SAMPLE_SIZES = (100, 1000, 5000)

_PHASES = ("Plan", "Design", "Build", "Review", "Test", "Integrate", "Document", "Deploy")
_SUBJECTS = ("API", "database", "login", "reports", "search", "billing", "settings", "dashboard",
             "exports", "notifications", "onboarding", "permissions")


def generate_sample(size: int, start_date: date = date(2026, 1, 5)) -> Project:
    """A valid project of ``size`` tasks; the same size always yields the same project."""
    rng = random.Random(size)
    year = start_date.year
    holidays = frozenset(
        d for y in (year, year + 1)
        for d in (date(y, 1, 1), date(y, 5, 1), date(y, 12, 25), date(y, 12, 26))
    )
    calendar = WorkCalendar(start_date, frozenset(range(5)), holidays)
    tasks: list[Task] = []
    for i in range(size):
        tid = i + 1
        if i > 0 and rng.random() < 0.05:
            duration = 0
            name = f"Milestone {tid}"
        else:
            duration = rng.randint(1, 12)
            name = f"{rng.choice(_PHASES)} {rng.choice(_SUBJECTS)} {tid}"
        preds: list[int] = []
        if i > 0:
            window = range(max(1, tid - 40), tid)
            count = min(len(window), rng.choice((1, 1, 1, 2, 2, 3)))
            preds = sorted(rng.sample(window, count))
        tasks.append(Task(tid, name, duration, preds))
    return Project(calendar=calendar, tasks=tasks, next_id=size + 1)
