from datetime import date

import pytest

from project_scheduler.domain import Project, Task, WorkCalendar
from project_scheduler.domain.validation import (
    ErrorCode,
    find_cycle,
    validate_calendar,
    validate_dependency,
    validate_duration,
    validate_name,
    validate_predecessor_set,
    validate_project,
)


def chain(n: int) -> Project:
    tasks = [Task(i, f"T{i}", 1, [i - 1] if i > 1 else []) for i in range(1, n + 1)]
    return Project(WorkCalendar(date(2026, 1, 5)), tasks, n + 1)


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_empty_name_rejected(name):
    assert validate_name(name).code is ErrorCode.EMPTY_NAME


def test_name_accepted():
    assert validate_name(" Build ") is None


@pytest.mark.parametrize("value", [-1, 10_000, 1.5, True, "3", None])
def test_bad_duration_rejected(value):
    err = validate_duration(value)
    assert err.code is ErrorCode.DURATION_RANGE
    assert err.data["max"] == 9999


@pytest.mark.parametrize("value", [0, 1, 9999])
def test_duration_accepted(value):
    assert validate_duration(value) is None


def test_cycle_of_length_one_is_self_dependency():
    assert validate_dependency(chain(2), 1, 1).code is ErrorCode.SELF_DEPENDENCY


def test_cycle_of_length_two():
    err = validate_dependency(chain(2), 2, 1)  # 2 already depends on 1
    assert err.code is ErrorCode.CYCLE
    assert err.data["path"] == (1, 2, 1)


def test_cycle_of_length_n():
    err = validate_dependency(chain(5), 5, 1)
    assert err.code is ErrorCode.CYCLE
    assert err.data["path"] == (1, 2, 3, 4, 5, 1)


def test_unknown_predecessor():
    err = validate_dependency(chain(2), 99, 2)
    assert err.code is ErrorCode.UNKNOWN_PREDECESSOR
    assert err.data["task_id"] == 99


def test_unknown_successor():
    assert validate_dependency(chain(2), 1, 99).code is ErrorCode.UNKNOWN_TASK


def test_duplicate_dependency():
    assert validate_dependency(chain(2), 1, 2).code is ErrorCode.DUPLICATE_DEPENDENCY


def test_valid_dependency():
    assert validate_dependency(chain(3), 1, 3) is None


def test_predecessor_set_for_new_task():
    p = chain(3)
    assert validate_predecessor_set(p, None, [1, 3]) is None
    assert validate_predecessor_set(p, None, [7]).code is ErrorCode.UNKNOWN_PREDECESSOR
    assert validate_predecessor_set(p, None, [1, 1]).code is ErrorCode.DUPLICATE_DEPENDENCY


def test_predecessor_set_replacing_edges_can_be_valid():
    p = chain(3)
    # Task 1 may depend on 3 once 2 no longer depends on 1.
    p.tasks[1].predecessors = []
    assert validate_predecessor_set(p, 1, [3]) is None
    assert validate_predecessor_set(p, 3, [1]) is None


def test_calendar_needs_a_working_day():
    assert validate_calendar([]).code is ErrorCode.NO_WORKING_DAYS
    assert validate_calendar([7]).code is ErrorCode.INVALID_WEEKDAY
    assert validate_calendar([0]) is None


def test_find_cycle_none_for_dag():
    assert find_cycle({1: [], 2: [1], 3: [1, 2]}) is None


def test_validate_project_reports_problems():
    cal = WorkCalendar(date(2026, 1, 5))
    assert validate_project(chain(4)) == []
    dup = Project(cal, [Task(1, "A", 1), Task(1, "B", 1)], 2)
    assert validate_project(dup)[0].code is ErrorCode.DUPLICATE_TASK_ID
    bad = Project(cal, [Task(1, " ", -2, [1, 5])], 2)
    codes = {e.code for e in validate_project(bad)}
    assert codes == {ErrorCode.EMPTY_NAME, ErrorCode.DURATION_RANGE, ErrorCode.SELF_DEPENDENCY,
                     ErrorCode.UNKNOWN_PREDECESSOR}
    cyclic = Project(cal, [Task(1, "A", 1, [2]), Task(2, "B", 1, [1])], 3)
    assert validate_project(cyclic)[0].code is ErrorCode.CYCLE
    stale = Project(cal, [Task(4, "A", 1)], 2)
    assert validate_project(stale)[0].code is ErrorCode.INVALID_NEXT_ID
