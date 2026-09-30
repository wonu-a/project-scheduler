from datetime import date

import pytest

from project_scheduler.domain import WorkCalendar

FRI = date(2026, 1, 2)
SAT = date(2026, 1, 3)
MON = date(2026, 1, 5)


def test_index_zero_is_start_when_start_is_a_working_day():
    assert WorkCalendar(FRI).index_to_date(0) == FRI


def test_weekend_start_moves_index_zero_to_next_working_day():
    cal = WorkCalendar(SAT)
    assert cal.index_to_date(0) == MON
    assert cal.date_to_index(SAT) == 0


def test_indices_skip_weekends():
    cal = WorkCalendar(FRI)
    assert [cal.index_to_date(i) for i in range(3)] == [FRI, MON, date(2026, 1, 6)]


def test_holidays_are_skipped():
    cal = WorkCalendar(MON, holidays=frozenset({date(2026, 1, 6)}))
    assert cal.index_to_date(1) == date(2026, 1, 7)


def test_non_working_day_rounds_forward():
    cal = WorkCalendar(FRI, holidays=frozenset({date(2026, 1, 6)}))
    assert cal.date_to_index(SAT) == cal.date_to_index(MON) == 1
    assert cal.date_to_index(date(2026, 1, 6)) == 2  # holiday -> Wednesday


def test_date_before_start_maps_to_zero():
    assert WorkCalendar(MON).date_to_index(date(2025, 12, 1)) == 0


def test_round_trip():
    cal = WorkCalendar(SAT, frozenset({0, 2, 4}), frozenset({date(2026, 3, 4)}))
    for i in range(500):
        assert cal.date_to_index(cal.index_to_date(i)) == i


def test_custom_working_weekdays():
    cal = WorkCalendar(MON, frozenset({5, 6}))  # weekends only
    assert cal.index_to_date(0) == date(2026, 1, 10)
    assert cal.index_to_date(1) == date(2026, 1, 11)


def test_calendar_without_working_days_is_rejected():
    with pytest.raises(ValueError):
        WorkCalendar(MON, frozenset())


def test_negative_index_is_rejected():
    with pytest.raises(ValueError):
        WorkCalendar(MON).index_to_date(-1)


def test_equality_ignores_lookup_cache():
    a, b = WorkCalendar(MON), WorkCalendar(MON)
    a.index_to_date(50)
    assert a == b
