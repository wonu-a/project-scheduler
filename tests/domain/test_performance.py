"""Loose performance guards. The budget is < 1 s for loading and scheduling 5 000 tasks."""

import time
from datetime import date

from project_scheduler.domain import Project, Task, WorkCalendar, compute_schedule
from project_scheduler.domain.validation import ErrorCode, validate_dependency, validate_project
from project_scheduler.samples import generate_sample

N = 5000


def long_chain() -> Project:
    tasks = [Task(i, f"T{i}", 1, [i - 1] if i > 1 else []) for i in range(1, N + 1)]
    return Project(WorkCalendar(date(2026, 1, 5)), tasks, N + 1)


def test_5000_chain_schedules_without_recursion():
    p = long_chain()
    start = time.perf_counter()
    s = compute_schedule(p)
    assert time.perf_counter() - start < 1.0
    assert s.finish_index == N
    assert s.critical_count == N


def test_5000_chain_cycle_detection_without_recursion():
    err = validate_dependency(long_chain(), N, 1)
    assert err.code is ErrorCode.CYCLE
    assert len(err.data["path"]) == N + 1


def test_5000_sample_generates_validates_and_schedules_quickly():
    start = time.perf_counter()
    p = generate_sample(N)
    assert validate_project(p) == []
    s = compute_schedule(p)
    s.project_finish_date()
    assert time.perf_counter() - start < 2.0  # loose bound for slow CI machines
    assert len(s.entries) == N
