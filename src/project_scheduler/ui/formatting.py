"""Locale-aware formatting at the UI boundary. Everything goes through QLocale()."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QLocale


def to_qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def from_qdate(d: QDate) -> date:
    return date(d.year(), d.month(), d.day())


def format_date(d: date, locale: QLocale | None = None) -> str:
    return (locale or QLocale()).toString(to_qdate(d), QLocale.FormatType.ShortFormat)


def format_number(n: int, locale: QLocale | None = None) -> str:
    return (locale or QLocale()).toString(n)


def id_locale() -> QLocale:
    """The current locale without group separators, for task ids (1234, not 1,234)."""
    locale = QLocale()
    locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator)
    return locale
