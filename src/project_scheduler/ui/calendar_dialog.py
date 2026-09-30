"""Edit the project start date, working weekdays and holidays."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QEvent, QLocale, Qt
from PySide6.QtGui import QIcon, QUndoStack
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..domain import ValidationError
from .commands import ChangeStartDateCommand, EditCalendarCommand
from .errors import error_text
from .formatting import format_date, from_qdate, to_qdate
from .sizing import reserve_wrapped_label_heights
from .session import ProjectSession


class CalendarDialog(QDialog):
    def __init__(self, session: ProjectSession, undo_stack: QUndoStack, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("calendarDialog")
        self.session = session
        self.undo_stack = undo_stack
        calendar = session.project.calendar

        self.title_label = QLabel(objectName="dialogTitle")
        self.start_caption = QLabel(objectName="sectionLabel")
        self.start_edit = QDateEdit(objectName="startDateEdit")
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDate(to_qdate(calendar.start_date))

        self.weekdays_caption = QLabel(objectName="sectionLabel")
        self.weekday_boxes: list[QCheckBox] = []
        weekday_grid = QGridLayout()
        # Explicit: the macOS style gives nested grids no horizontal gap, so labels ran into the next box.
        weekday_grid.setHorizontalSpacing(16)
        weekday_grid.setVerticalSpacing(6)
        for weekday in range(7):  # 0 = Monday, as in datetime.date.weekday()
            box = QCheckBox(objectName="weekdayCheck")
            box.setChecked(weekday in calendar.working_weekdays)
            self.weekday_boxes.append(box)
            weekday_grid.addWidget(box, weekday // 4, weekday % 4)

        self.holidays_caption = QLabel(objectName="sectionLabel")
        self.holiday_edit = QDateEdit(objectName="holidayEdit")
        self.holiday_edit.setCalendarPopup(True)
        self.holiday_edit.setDate(to_qdate(calendar.start_date))
        self.add_holiday_button = QPushButton(QIcon(":/icons/add.svg"), "", objectName="addHolidayButton")
        self.add_holiday_button.clicked.connect(self._add_holiday)
        self.holiday_list = QListWidget(objectName="holidayList")
        self.holiday_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.remove_holiday_button = QPushButton(QIcon(":/icons/delete.svg"), "", objectName="removeHolidayButton")
        self.remove_holiday_button.clicked.connect(self._remove_selected_holidays)
        self.holiday_list.itemSelectionChanged.connect(self._update_remove_button)
        # Shown instead of the list while there are no holidays; an empty list box looks like a text field.
        self.holiday_hint = QLabel(objectName="emptyHint")
        self.holiday_hint.setWordWrap(True)
        self._holidays: set[date] = set(calendar.holidays)

        self.error_label = QLabel(objectName="errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        # Our own OK button: a standard one gets Qt's text back on every language change.
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.buttons.addButton("", QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok_button.setDefault(True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        holiday_row = QHBoxLayout()
        holiday_row.addWidget(self.holiday_edit, 1)
        holiday_row.addWidget(self.add_holiday_button)
        holiday_row.addWidget(self.remove_holiday_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.start_caption)
        layout.addWidget(self.start_edit)
        layout.addWidget(self.weekdays_caption)
        layout.addLayout(weekday_grid)
        layout.addWidget(self.holidays_caption)
        layout.addLayout(holiday_row)
        layout.addWidget(self.holiday_list, 1)
        layout.addWidget(self.holiday_hint)
        layout.addWidget(self.error_label)
        layout.addStretch(0)  # takes the spare height while the list is hidden
        self._spacer_index = layout.count() - 1
        layout.addWidget(self.buttons)
        self.resize(440, 520)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.ok_button.setText(self.tr("OK"))
        locale = QLocale()
        self.setWindowTitle(self.tr("Project calendar"))
        self.title_label.setText(self.tr("Project calendar"))
        self.start_caption.setText(self.tr("Project start date"))
        self.weekdays_caption.setText(self.tr("Working days"))
        self.holidays_caption.setText(self.tr("Holidays"))
        self.add_holiday_button.setText(self.tr("Add"))
        self.remove_holiday_button.setText(self.tr("Remove"))
        date_format = locale.dateFormat(QLocale.FormatType.ShortFormat)
        self.start_edit.setDisplayFormat(date_format)
        self.holiday_edit.setDisplayFormat(date_format)
        for weekday, box in enumerate(self.weekday_boxes):
            box.setText(locale.dayName(weekday + 1, QLocale.FormatType.LongFormat))  # Qt: Monday is 1
        self.holiday_hint.setText(self.tr("No holidays yet. Pick a date above and add it."))
        self._refresh_holiday_list()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def _refresh_holiday_list(self) -> None:
        self.holiday_list.clear()
        for day in sorted(self._holidays):
            item = QListWidgetItem(format_date(day))
            item.setData(Qt.ItemDataRole.UserRole, QDate(to_qdate(day)))
            self.holiday_list.addItem(item)
        has_holidays = bool(self._holidays)
        self.holiday_list.setVisible(has_holidays)
        self.holiday_hint.setVisible(not has_holidays)
        self.layout().setStretch(self._spacer_index, 0 if has_holidays else 1)
        self._update_remove_button()
        self._reserve_label_heights()

    def _update_remove_button(self) -> None:
        self.remove_holiday_button.setEnabled(bool(self.holiday_list.selectedItems()))

    def _reserve_label_heights(self) -> None:
        reserve_wrapped_label_heights(self.layout(), [self.holiday_hint, self.error_label])

    def _add_holiday(self) -> None:
        self._holidays.add(from_qdate(self.holiday_edit.date()))
        self._refresh_holiday_list()

    def _remove_selected_holidays(self) -> None:
        for item in self.holiday_list.selectedItems():
            self._holidays.discard(from_qdate(item.data(Qt.ItemDataRole.UserRole)))
        self._refresh_holiday_list()

    def working_weekdays(self) -> set[int]:
        return {i for i, box in enumerate(self.weekday_boxes) if box.isChecked()}

    def holidays(self) -> set[date]:
        return set(self._holidays)

    def accept(self) -> None:
        calendar_cmd = EditCalendarCommand.create(self.session, self.working_weekdays(), self._holidays)
        if isinstance(calendar_cmd, ValidationError):
            self.error_label.setText(error_text(calendar_cmd, self.session.name_of))
            self.error_label.show()
            self._reserve_label_heights()
            return
        start = from_qdate(self.start_edit.date())
        changes_start = start != self.session.project.calendar.start_date
        if calendar_cmd is not None and changes_start:
            self.undo_stack.beginMacro(self.tr("Edit calendar"))
        if calendar_cmd is not None:
            self.undo_stack.push(calendar_cmd)
        if changes_start:
            # Created after the calendar edit so it keeps the new weekdays and holidays.
            self.undo_stack.push(ChangeStartDateCommand.create(self.session, start))
        if calendar_cmd is not None and changes_start:
            self.undo_stack.endMacro()
        super().accept()
