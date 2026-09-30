"""Translated text for validation error codes and load results."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from ..domain import ErrorCode, ValidationError
from ..storage import MessageCode
from .formatting import format_number, id_locale



def error_text(error: ValidationError, name_of: Callable[[int], str]) -> str:
    code, data = error.code, error.data
    if code is ErrorCode.EMPTY_NAME:
        return QCoreApplication.translate("Errors", "The task name must not be empty.")
    if code is ErrorCode.DURATION_RANGE:
        return QCoreApplication.translate("Errors", "The duration must be a whole number from {0} to {1}.").format(
            format_number(data["min"]), format_number(data["max"])
        )
    if code is ErrorCode.SELF_DEPENDENCY:
        return QCoreApplication.translate("Errors", "Task “{0}” cannot depend on itself.").format(name_of(data["task_id"]))
    if code is ErrorCode.UNKNOWN_PREDECESSOR:
        return QCoreApplication.translate("Errors", "Task {0} does not exist.").format(id_locale().toString(data["task_id"]))
    if code is ErrorCode.DUPLICATE_DEPENDENCY:
        return QCoreApplication.translate("Errors", "“{0}” already depends on “{1}”.").format(
            name_of(data["successor"]), name_of(data["predecessor"])
        )
    if code is ErrorCode.CYCLE:
        separator = QCoreApplication.translate("Errors", " → ")
        path = separator.join(name_of(tid) for tid in data["path"])
        return QCoreApplication.translate("Errors", "This dependency would create a cycle: {0}").format(path)
    if code is ErrorCode.NO_WORKING_DAYS:
        return QCoreApplication.translate("Errors", "Select at least one working day.")
    if code is ErrorCode.INVALID_WEEKDAY:
        return QCoreApplication.translate("Errors", "The calendar contains an invalid weekday.")
    if code is ErrorCode.UNKNOWN_TASK:
        return QCoreApplication.translate("Errors", "The task no longer exists.")
    if code is ErrorCode.DUPLICATE_TASK_ID:
        return QCoreApplication.translate("Errors", "Two tasks share the id {0}.").format(id_locale().toString(data["task_id"]))
    return QCoreApplication.translate("Errors", "The project data is inconsistent.")


def load_message(code: MessageCode, path: Path, backup: Path | None) -> str:
    name = path.name
    if code is MessageCode.FILE_MISSING:
        return QCoreApplication.translate("Errors", "The file {0} was not found. Starting with an empty project.").format(name)
    if code is MessageCode.FILE_CORRUPT:
        return QCoreApplication.translate("Errors", 
            "The file {0} could not be read. A copy was kept as {1}. Starting with an empty project."
        ).format(name, backup.name if backup else "")
    if code is MessageCode.FILE_CORRUPT_NOT_BACKED_UP:
        return QCoreApplication.translate("Errors", "The file {0} could not be read. Starting with an empty project.").format(name)
    if code is MessageCode.FILE_TOO_NEW:
        return QCoreApplication.translate("Errors", 
            "The file {0} was saved by a newer version of Project Scheduler and cannot be opened."
        ).format(name)
    if code is MessageCode.FILE_MIGRATED:
        return QCoreApplication.translate("Errors", "The file {0} was upgraded from an older format. Save it to keep the new format.").format(name)
    return ""


def save_failed_text(path: Path, reason: str) -> str:
    return QCoreApplication.translate("Errors", "The file {0} could not be saved: {1}").format(path.name, reason)
