"""Table model for the task list. ``data()`` is O(1): display strings are cached per locale."""

from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QLocale, QModelIndex, QObject, QPersistentModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QIcon

from .formatting import format_date, id_locale
from .i18n import language_manager
from .session import ProjectSession
from .theme import theme_manager

SORT_ROLE = Qt.ItemDataRole.UserRole + 1
TASK_ID_ROLE = Qt.ItemDataRole.UserRole + 2


class Column(IntEnum):
    ID = 0
    NAME = 1
    DURATION = 2
    PREDECESSORS = 3
    START = 4
    FINISH = 5
    LATE_START = 6
    LATE_FINISH = 7
    SLACK = 8
    CRITICAL = 9


_NUMERIC = {Column.ID, Column.DURATION, Column.SLACK}
_EDITABLE = {Column.NAME, Column.DURATION}

# Called with (task_id, column, value); returns True if the edit was accepted.
EditHandler = Callable[[int, Column, Any], bool]


class TaskTableModel(QAbstractTableModel):
    def __init__(self, session: ProjectSession, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.edit_handler: EditHandler | None = None
        self._rows: list[list[str]] = []
        self._critical_icon = QIcon(":/icons/critical.svg")

        session.rowsAboutToBeInserted.connect(self._on_about_to_insert)
        session.rowsInserted.connect(self._on_inserted)
        session.rowsAboutToBeRemoved.connect(self._on_about_to_remove)
        session.rowsRemoved.connect(self._on_removed)
        session.aboutToReset.connect(self.beginResetModel)
        session.reset.connect(self._on_reset)
        session.scheduleChanged.connect(self._on_schedule_changed)
        language_manager.languageChanged.connect(self._on_language_changed)
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._rebuild_cache()

    # --- cache -------------------------------------------------------------------------------

    def _rebuild_cache(self) -> None:
        locale = QLocale()
        ids = id_locale()
        schedule = self.session.schedule
        calendar = schedule.calendar
        dates: dict[int, str] = {}
        numbers: dict[int, str] = {}
        separator = self.tr(", ")
        critical_text = self.tr("Critical")

        def date_at(index: int) -> str:
            text = dates.get(index)
            if text is None:
                text = dates[index] = format_date(calendar.index_to_date(index), locale)
            return text

        def number(n: int) -> str:
            text = numbers.get(n)
            if text is None:
                text = numbers[n] = locale.toString(n)
            return text

        rows = []
        for task in self.session.project.tasks:
            t = schedule[task.id]
            last_day = t.ef - 1 if t.duration > 0 else t.es
            late_last_day = t.lf - 1 if t.duration > 0 else t.ls
            rows.append([
                ids.toString(task.id),
                task.name,
                number(task.duration),
                separator.join(ids.toString(p) for p in task.predecessors),
                date_at(t.es),
                date_at(last_day),
                date_at(t.ls),
                date_at(late_last_day),
                number(t.slack),
                critical_text if t.critical else "",
            ])
        self._rows = rows

    def _emit_all_changed(self, roles: list[int] | None = None) -> None:
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0), self.index(len(self._rows) - 1, len(Column) - 1), roles or []
            )

    # --- session signal handlers ------------------------------------------------------------

    def _on_about_to_insert(self, first: int, last: int) -> None:
        self.beginInsertRows(QModelIndex(), first, last)
        self._pending_insert = (first, last)

    def _on_inserted(self) -> None:
        first, last = self._pending_insert
        # Placeholders until the schedule is recomputed, which the command does right after.
        self._rows[first:first] = [[""] * len(Column) for _ in range(last - first + 1)]
        self.endInsertRows()

    def _on_about_to_remove(self, first: int, last: int) -> None:
        self.beginRemoveRows(QModelIndex(), first, last)

    def _on_removed(self, first: int, last: int) -> None:
        del self._rows[first : last + 1]
        self.endRemoveRows()

    def _on_reset(self) -> None:
        self._rebuild_cache()
        self.endResetModel()

    def _on_schedule_changed(self) -> None:
        self._rebuild_cache()
        self._emit_all_changed()

    def _on_language_changed(self, _code: str) -> None:
        self._rebuild_cache()
        self._emit_all_changed()
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(Column) - 1)

    def _on_theme_changed(self, _name: str) -> None:
        self._emit_all_changed([Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole])

    # --- Qt model API -----------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(Column)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.column_title(Column(section))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if section in _NUMERIC:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def column_title(self, column: Column) -> str:
        return {
            Column.ID: self.tr("ID"),
            Column.NAME: self.tr("Name"),
            Column.DURATION: self.tr("Duration (days)"),
            Column.PREDECESSORS: self.tr("Predecessors"),
            Column.START: self.tr("Start"),
            Column.FINISH: self.tr("Finish"),
            Column.LATE_START: self.tr("Latest start"),
            Column.LATE_FINISH: self.tr("Latest finish"),
            Column.SLACK: self.tr("Slack (days)"),
            Column.CRITICAL: self.tr("Critical path"),
        }[column]

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() in _EDITABLE:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return self._rows[row][col]
        task = self.session.project.tasks[row]
        if role == Qt.ItemDataRole.EditRole:
            if col == Column.NAME:
                return task.name
            if col == Column.DURATION:
                return task.duration
            return self._rows[row][col]
        if role == TASK_ID_ROLE:
            return task.id
        if role == Qt.ItemDataRole.ToolTipRole and col == Column.NAME:
            return task.notes or None  # hovering a task's name shows its notes
        times = self.session.schedule.entries.get(task.id)
        if times is None:  # row inserted, schedule not yet recomputed
            return None
        if role == SORT_ROLE:
            return (
                task.id, task.name.casefold(), task.duration, len(task.predecessors),
                times.es, times.ef, times.ls, times.lf, times.slack, 0 if times.critical else 1,
            )[col]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in _NUMERIC:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        palette = theme_manager.palette
        if role == Qt.ItemDataRole.BackgroundRole and times.critical:
            return palette.critical_background
        if role == Qt.ItemDataRole.ForegroundRole:
            if times.critical:
                return palette.critical_foreground
            if task.duration == 0:
                return palette.milestone_foreground
        if role == Qt.ItemDataRole.DecorationRole and col == Column.CRITICAL and times.critical:
            return self._critical_icon
        return None

    def setData(self, index: QModelIndex | QPersistentModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or index.column() not in _EDITABLE:
            return False
        if self.edit_handler is None:
            return False
        task_id = self.session.project.tasks[index.row()].id
        return self.edit_handler(task_id, Column(index.column()), value)

    def task_id_at(self, row: int) -> int:
        return self.session.project.tasks[row].id


class PredecessorListModel(QAbstractTableModel):
    """Checkable list of candidate predecessors for the task dialog (one column)."""

    def __init__(self, session: ProjectSession, exclude: int | None, checked: list[int], parent: QObject | None = None) -> None:
        super().__init__(parent)
        ids = id_locale()
        self._items = [
            (t.id, self.tr("{0} · {1}").format(ids.toString(t.id), t.name))
            for t in session.project.tasks
            if t.id != exclude
        ]
        # Keep the task's existing order; newly checked ids are appended.
        self._checked: list[int] = list(checked)

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else 1

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        task_id, text = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return text
        if role == Qt.ItemDataRole.CheckStateRole:
            return Qt.CheckState.Checked if task_id in self._checked else Qt.CheckState.Unchecked
        if role == TASK_ID_ROLE:
            return task_id
        return None

    def setData(self, index: QModelIndex | QPersistentModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.CheckStateRole or not index.isValid():
            return False
        task_id = self._items[index.row()][0]
        checked = Qt.CheckState(value) == Qt.CheckState.Checked
        if checked and task_id not in self._checked:
            self._checked.append(task_id)
        elif not checked and task_id in self._checked:
            self._checked.remove(task_id)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
        return True

    def set_checked(self, task_id: int, checked: bool) -> None:
        for row, (tid, _) in enumerate(self._items):
            if tid == task_id:
                self.setData(self.index(row, 0), Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked,
                             Qt.ItemDataRole.CheckStateRole)
                return

    def checked_ids(self) -> list[int]:
        return list(self._checked)


class TaskFilterProxy(QSortFilterProxyModel):
    """Sorting plus two filters: the name filter text, and optionally critical tasks only."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._critical_only = False

    @property
    def critical_only(self) -> bool:
        return self._critical_only

    def set_critical_only(self, value: bool) -> None:
        if value != self._critical_only:
            self.beginFilterChange()
            self._critical_only = value
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):  # the name filter
            return False
        if not self._critical_only:
            return True
        model = self.sourceModel()
        times = model.session.schedule.entries.get(model.task_id_at(source_row))
        return times is not None and times.critical
