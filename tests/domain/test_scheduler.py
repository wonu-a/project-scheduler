from datetime import date

import pytest

from project_scheduler.domain import Project, Task, WorkCalendar, compute_schedule


def project(*tasks: Task, start=date(2026, 1, 2), holidays=()) -> Project:
    return Project(
        WorkCalendar(start, holidays=frozenset(holidays)),
        list(tasks),
        next_id=max((t.id for t in tasks), default=0) + 1,
    )


def test_empty_project():
    s = compute_schedule(project())
    assert dict(s.entries) == {}
    assert s.finish_index == 0
    assert s.project_finish_date() is None
    assert s.critical_count == 0


def test_single_milestone():
    s = compute_schedule(project(Task(1, "M", 0)))
    t = s[1]
    assert (t.es, t.ef, t.ls, t.lf) == (0, 0, 0, 0)
    assert t.critical
    assert s.start_date(1) == s.finish_date(1) == date(2026, 1, 2)


def test_hand_worked_chain_example():
    # A (3d) -> B (2d), start Fri 2026-01-02, Mon-Fri. Index 0 = Fri Jan 2.
    s = compute_schedule(project(Task(1, "A", 3), Task(2, "B", 2, [1])))
    assert (s[1].es, s[1].ef) == (0, 3)
    assert (s[2].es, s[2].ef) == (3, 5)
    assert (s.start_date(1), s.finish_date(1)) == (date(2026, 1, 2), date(2026, 1, 6))
    assert (s.start_date(2), s.finish_date(2)) == (date(2026, 1, 7), date(2026, 1, 8))
    assert s.project_finish_date() == date(2026, 1, 8)
    assert s[1].critical and s[2].critical


def test_diamond():
    #      B(3)
    # A(2)      D(2)
    #      C(1)
    s = compute_schedule(project(
        Task(1, "A", 2), Task(2, "B", 3, [1]), Task(3, "C", 1, [1]), Task(4, "D", 2, [2, 3]),
    ))
    assert {k: (v.es, v.ef, v.ls, v.lf) for k, v in s.entries.items()} == {
        1: (0, 2, 0, 2),
        2: (2, 5, 2, 5),
        3: (2, 3, 4, 5),
        4: (5, 7, 5, 7),
    }
    assert s[3].slack == 2
    assert [tid for tid, t in s.entries.items() if t.critical] == [1, 2, 4]
    assert s.finish_index == 7


def test_task_without_successors_gets_project_finish_as_late_finish():
    s = compute_schedule(project(Task(1, "long", 5), Task(2, "short", 1)))
    assert s[2].lf == 5
    assert s[2].ls == 4
    assert s[2].slack == 4
    assert not s[2].critical


def test_holiday_inside_task_span():
    s = compute_schedule(project(Task(1, "A", 3), start=date(2026, 1, 5), holidays={date(2026, 1, 7)}))
    assert s.start_date(1) == date(2026, 1, 5)
    assert s.finish_date(1) == date(2026, 1, 8)


def test_weekend_start_date():
    s = compute_schedule(project(Task(1, "A", 1), start=date(2026, 1, 3)))
    assert s.start_date(1) == s.finish_date(1) == date(2026, 1, 5)


def test_milestone_after_task_shows_single_date():
    s = compute_schedule(project(Task(1, "A", 2), Task(2, "M", 0, [1])))
    assert s[2].es == s[2].ef == 2
    assert s.start_date(2) == s.finish_date(2) == date(2026, 1, 6)


def test_late_dates():
    s = compute_schedule(project(Task(1, "long", 5), Task(2, "short", 1)))
    assert s.late_start_date(2) == s.late_finish_date(2) == date(2026, 1, 8)


def test_cycle_raises():
    with pytest.raises(ValueError):
        compute_schedule(project(Task(1, "A", 1, [2]), Task(2, "B", 1, [1])))


def test_schedule_is_immutable_and_tasks_are_untouched():
    p = project(Task(1, "A", 1))
    s = compute_schedule(p)
    with pytest.raises(TypeError):
        s.entries[1] = None  # type: ignore[index]
    assert not hasattr(p.tasks[0], "es")


def test_notes_never_affect_the_schedule():
    plain = project(Task(1, "A", 3), Task(2, "B", 2, [1]))
    noted = project(Task(1, "A", 3, notes="call vendor"), Task(2, "B", 2, [1], notes="x" * 5000))
    assert compute_schedule(plain).entries == compute_schedule(noted).entries


def test_task_copy_keeps_notes_independent():
    task = Task(1, "A", 1, [], notes="original")
    copy = task.copy()
    assert copy == task
    copy.notes = "changed"
    assert task.notes == "original"
