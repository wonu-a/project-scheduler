"""Working-day calendar: converts between dates and working-day indices.

Index 0 is the first working day on or after the project start date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

MONDAY_TO_FRIDAY = frozenset({0, 1, 2, 3, 4})  # date.weekday(): Monday is 0


@dataclass(frozen=True)
class WorkCalendar:
    start_date: date
    working_weekdays: frozenset[int] = MONDAY_TO_FRIDAY
    holidays: frozenset[date] = frozenset()

    # Lazily extended lookup tables. Not part of equality.
    _dates: list[date] = field(default_factory=list, init=False, repr=False, compare=False)
    _index: dict[date, int] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "working_weekdays", frozenset(self.working_weekdays))
        object.__setattr__(self, "holidays", frozenset(self.holidays))
        if not self.working_weekdays:
            # validation.validate_calendar reports this to the user; reaching it is a bug.
            raise ValueError("a calendar needs at least one working weekday")

    def is_working_day(self, d: date) -> bool:
        return d.weekday() in self.working_weekdays and d not in self.holidays

    def with_start_date(self, start_date: date) -> WorkCalendar:
        return WorkCalendar(start_date, self.working_weekdays, self.holidays)

    def index_to_date(self, index: int) -> date:
        if index < 0:
            raise ValueError(f"working-day index must be >= 0, got {index}")
        self._extend_to_index(index)
        return self._dates[index]

    def date_to_index(self, d: date) -> int:
        """Index of ``d``; a non-working day rounds forward, a date before the start maps to 0."""
        if d <= self.start_date:
            return 0
        while not self.is_working_day(d):
            d += timedelta(days=1)
        self._extend_to_date(d)
        return self._index[d]

    def _append_next(self) -> None:
        d = self._dates[-1] + timedelta(days=1) if self._dates else self.start_date
        while not self.is_working_day(d):
            d += timedelta(days=1)
        self._index[d] = len(self._dates)
        self._dates.append(d)

    def _extend_to_index(self, index: int) -> None:
        while len(self._dates) <= index:
            self._append_next()

    def _extend_to_date(self, d: date) -> None:
        while not self._dates or self._dates[-1] < d:
            self._append_next()
