from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QUndoStack

from project_scheduler.ui.calendar_dialog import CalendarDialog
from project_scheduler.ui.task_dialog import TaskDialog


def make_task_dialog(qtbot, session, task_id=None):
    stack = QUndoStack()
    dialog = TaskDialog(session, stack, task_id)
    qtbot.addWidget(dialog)
    dialog.show()
    return dialog, stack


def check(dialog, task_id, checked=True):
    dialog.predecessors.set_checked(task_id, checked)


# --- task dialog ---------------------------------------------------------------------------

def test_task_dialog_opens_empty_for_new_task(qtbot, session):
    dialog, _ = make_task_dialog(qtbot, session)
    assert dialog.isVisible()
    assert dialog.windowTitle() == "New task"
    assert dialog.name_edit.text() == ""
    assert dialog.predecessors.rowCount() == 4


def test_task_dialog_add_ok_pushes_command(qtbot, session):
    dialog, stack = make_task_dialog(qtbot, session)
    qtbot.keyClicks(dialog.name_edit, "Review")
    dialog.duration_spin.setValue(2)
    check(dialog, 4)
    dialog.ok_button.click()
    assert dialog.result() == dialog.DialogCode.Accepted
    assert stack.count() == 1
    task = session.project.tasks[-1]
    assert (task.name, task.duration, task.predecessors) == ("Review", 2, [4])


def test_task_dialog_cancel_changes_nothing(qtbot, session):
    dialog, stack = make_task_dialog(qtbot, session)
    qtbot.keyClicks(dialog.name_edit, "Review")
    dialog.buttons.button(dialog.buttons.StandardButton.Cancel).click()
    assert dialog.result() == dialog.DialogCode.Rejected
    assert stack.count() == 0
    assert len(session.project.tasks) == 4


def test_task_dialog_empty_name_shows_error_and_stays_open(qtbot, session):
    dialog, stack = make_task_dialog(qtbot, session)
    dialog.ok_button.click()
    assert dialog.isVisible()
    assert dialog.error_label.isVisible()
    assert "name" in dialog.error_label.text()
    assert stack.count() == 0


def test_task_dialog_edit_prefills_and_rejects_cycle(qtbot, session):
    dialog, stack = make_task_dialog(qtbot, session, task_id=1)
    assert dialog.name_edit.text() == "Design"
    assert dialog.duration_spin.value() == 3
    assert dialog.predecessors.rowCount() == 3  # itself is not offered
    check(dialog, 4)  # Launch depends (indirectly) on Design
    dialog.accept()
    assert dialog.isVisible()
    assert "cycle" in dialog.error_label.text()
    assert "Design → Build → Launch → Design" in dialog.error_label.text()
    assert stack.count() == 0


def test_task_dialog_edit_is_one_undo_step(qtbot, session):
    dialog, stack = make_task_dialog(qtbot, session, task_id=4)
    dialog.name_edit.setText("Go live")
    dialog.duration_spin.setValue(2)
    check(dialog, 2, False)
    check(dialog, 1)
    dialog.accept()
    task = session.project.find(4)
    assert (task.name, task.duration, task.predecessors) == ("Go live", 2, [3, 1])
    assert stack.count() == 1
    stack.undo()
    assert (task.name, task.duration, task.predecessors) == ("Launch", 1, [2, 3])


def test_task_dialog_without_other_tasks_shows_hint_not_empty_list(qtbot):
    from project_scheduler.domain import Project
    from project_scheduler.ui.session import ProjectSession

    dialog, stack = make_task_dialog(qtbot, ProjectSession(Project.new(date(2026, 1, 5))))
    assert dialog.no_predecessors_hint.isVisible()
    assert not dialog.predecessor_view.isVisible()
    assert not dialog.filter_edit.isVisible()
    qtbot.keyClicks(dialog.name_edit, "First")
    dialog.accept()
    assert stack.count() == 1


def test_task_dialog_with_other_tasks_shows_list(qtbot, session):
    dialog, _ = make_task_dialog(qtbot, session)
    assert dialog.predecessor_view.isVisible()
    assert not dialog.no_predecessors_hint.isVisible()


def test_task_dialog_name_field_grows_and_fits_placeholder(qtbot, session):
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QFormLayout

    dialog, _ = make_task_dialog(qtbot, session)
    # Must not depend on the platform style (macOS defaults to FieldsStayAtSizeHint).
    assert dialog.form.fieldGrowthPolicy() == QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
    placeholder = QFontMetrics(dialog.name_edit.font()).horizontalAdvance(dialog.name_edit.placeholderText())
    assert dialog.name_edit.width() > placeholder
    narrow = dialog.name_edit.width()
    dialog.resize(dialog.width() + 200, dialog.height())
    qtbot.waitUntil(lambda: dialog.name_edit.width() > narrow)


def test_task_dialog_smallest_size_does_not_cut_off_fields(qtbot, session):
    from project_scheduler.ui.i18n import language_manager

    dialog, _ = make_task_dialog(qtbot, session)
    dialog.duration_spin.setValue(9999)  # widest value
    for code in ("en", "de", "ja"):  # switched while open: minimums must follow the new text
        language_manager.set_language(code)
        qtbot.waitUntil(lambda: dialog.windowTitle() != "" and (code == "en") == (dialog.windowTitle() == "New task"))
        dialog.resize(1, 1)  # a window can't go below its layout's minimum
        qtbot.waitUntil(lambda: dialog.width() == dialog.minimumWidth() > 1)
        for edit in (dialog.name_edit, dialog.filter_edit):
            text_width = edit.fontMetrics().horizontalAdvance(edit.placeholderText())
            assert edit.width() >= edit.minimumWidth() > text_width, (code, edit.objectName())
        spin = dialog.duration_spin
        assert spin.width() >= spin.sizeHint().width(), code


def test_task_dialog_smallest_size_does_not_squeeze_fields_vertically(qtbot, session):
    """Word-wrapped labels (hint, error) must not squeeze the other rows at the minimum size."""
    from project_scheduler.domain import Project
    from project_scheduler.domain.validation import ErrorCode, ValidationError
    from project_scheduler.ui.i18n import language_manager
    from project_scheduler.ui.session import ProjectSession

    empty = ProjectSession(Project.new(date(2026, 1, 5)))
    for code in ("en", "de", "ja"):
        language_manager.set_language(code)
        for dialog_session, error in ((empty, ErrorCode.EMPTY_NAME), (session, ErrorCode.CYCLE)):
            dialog, _ = make_task_dialog(qtbot, dialog_session)
            for show_error in (False, True):
                if show_error:
                    dialog.show_error(ValidationError(error, {"path": (1, 2, 4, 1)}))
                dialog.resize(1, 1)
                qtbot.waitUntil(lambda: dialog.height() == dialog.minimumHeight() > 1)
                for field in (dialog.name_edit, dialog.duration_spin, dialog.filter_edit):
                    if field.isVisible():
                        assert field.height() >= field.sizeHint().height(), (code, field.objectName(), show_error)
                for label in (dialog.no_predecessors_hint, dialog.error_label):
                    if label.isVisible():
                        assert label.height() >= label.heightForWidth(label.width()), (code, label.objectName())
            dialog.reject()


def test_task_dialog_filter(qtbot, session):
    dialog, _ = make_task_dialog(qtbot, session)
    qtbot.keyClicks(dialog.filter_edit, "doc")
    assert dialog.proxy.rowCount() == 1


# --- calendar dialog -----------------------------------------------------------------------

def make_calendar_dialog(qtbot, session):
    stack = QUndoStack()
    dialog = CalendarDialog(session, stack)
    qtbot.addWidget(dialog)
    dialog.show()
    return dialog, stack


def test_calendar_dialog_opens_with_current_values(qtbot, session):
    dialog, _ = make_calendar_dialog(qtbot, session)
    assert dialog.isVisible()
    assert dialog.start_edit.date() == QDate(2026, 1, 2)
    assert dialog.working_weekdays() == {0, 1, 2, 3, 4}
    assert dialog.weekday_boxes[0].text() == "Monday"


def test_calendar_dialog_ok_is_one_undo_step(qtbot, session):
    dialog, stack = make_calendar_dialog(qtbot, session)
    dialog.start_edit.setDate(QDate(2026, 1, 5))
    dialog.weekday_boxes[4].setChecked(False)  # no Fridays
    dialog.holiday_edit.setDate(QDate(2026, 1, 6))
    qtbot.mouseClick(dialog.add_holiday_button, Qt.MouseButton.LeftButton)
    assert dialog.holiday_list.count() == 1
    dialog.ok_button.click()
    cal = session.project.calendar
    assert cal.start_date == date(2026, 1, 5)
    assert cal.working_weekdays == {0, 1, 2, 3}
    assert cal.holidays == {date(2026, 1, 6)}
    assert stack.count() == 1
    stack.undo()
    assert session.project.calendar.start_date == date(2026, 1, 2)
    assert session.project.calendar.holidays == frozenset()


def test_calendar_dialog_remove_holiday(qtbot, session):
    dialog, _ = make_calendar_dialog(qtbot, session)
    qtbot.mouseClick(dialog.add_holiday_button, Qt.MouseButton.LeftButton)
    dialog.holiday_list.item(0).setSelected(True)
    qtbot.mouseClick(dialog.remove_holiday_button, Qt.MouseButton.LeftButton)
    assert dialog.holiday_list.count() == 0


def test_calendar_dialog_requires_a_working_day(qtbot, session):
    dialog, stack = make_calendar_dialog(qtbot, session)
    for box in dialog.weekday_boxes:
        box.setChecked(False)
    dialog.accept()
    assert dialog.isVisible()
    assert dialog.error_label.text() == "Select at least one working day."
    assert stack.count() == 0


def test_calendar_dialog_shows_hint_instead_of_empty_holiday_list(qtbot, session):
    dialog, _ = make_calendar_dialog(qtbot, session)
    assert dialog.holiday_hint.isVisible()
    assert not dialog.holiday_list.isVisible()
    assert not dialog.remove_holiday_button.isEnabled()
    qtbot.mouseClick(dialog.add_holiday_button, Qt.MouseButton.LeftButton)
    assert dialog.holiday_list.isVisible()
    assert not dialog.holiday_hint.isVisible()
    dialog.holiday_list.item(0).setSelected(True)
    assert dialog.remove_holiday_button.isEnabled()
    qtbot.mouseClick(dialog.remove_holiday_button, Qt.MouseButton.LeftButton)
    assert dialog.holiday_hint.isVisible()


def test_calendar_dialog_smallest_size_does_not_cut_off_widgets(qtbot, session):
    from project_scheduler.ui.i18n import language_manager

    for code in ("en", "de", "ja"):
        language_manager.set_language(code)
        dialog, _ = make_calendar_dialog(qtbot, session)
        for show_error in (False, True):
            if show_error:
                for box in dialog.weekday_boxes:
                    box.setChecked(False)
                dialog.accept()
            dialog.resize(1, 1)
            qtbot.waitUntil(lambda: dialog.height() == dialog.minimumHeight() > 1)
            widgets = [dialog.start_edit, dialog.holiday_edit, dialog.add_holiday_button,
                       dialog.remove_holiday_button, *dialog.weekday_boxes]
            for w in widgets:
                assert w.width() >= w.sizeHint().width(), (code, w.objectName(), w.text() if hasattr(w, "text") else "")
                assert w.height() >= w.sizeHint().height(), (code, w.objectName())
            for label in (dialog.holiday_hint, dialog.error_label):
                if label.isVisible():
                    assert label.height() >= label.heightForWidth(label.width()), (code, label.objectName())
            # neighbouring weekday boxes must not overlap
            first, second = dialog.weekday_boxes[0], dialog.weekday_boxes[1]
            assert first.geometry().right() < second.geometry().left(), code
        dialog.reject()


def test_calendar_dialog_cancel_changes_nothing(qtbot, session):
    dialog, stack = make_calendar_dialog(qtbot, session)
    dialog.weekday_boxes[0].setChecked(False)
    dialog.reject()
    assert stack.count() == 0
    assert session.project.calendar.working_weekdays == {0, 1, 2, 3, 4}


def test_clicking_a_date_field_never_changes_its_date(qtbot, session):
    """Clicks on the closed date field used to add a year. Only the popup and typing change it."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QAbstractSpinBox

    dialog, _ = make_calendar_dialog(qtbot, session)
    for edit in (dialog.start_edit, dialog.holiday_edit):
        assert edit.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
        before = edit.date()
        for fx in (0.1, 0.3, 0.5, 0.7, 0.85):
            for fy in (0.2, 0.5, 0.8):
                point = QPoint(int(edit.width() * fx), int(edit.height() * fy))
                qtbot.mouseMove(edit, point)  # real clicks come with hover movement
                qtbot.mouseClick(edit, Qt.MouseButton.LeftButton, pos=point)
                assert edit.date() == before, (edit.objectName(), fx, fy)
    # typing still works: Up on the year section moves one year
    edit = dialog.start_edit
    year = edit.date().year()
    edit.setFocus()
    edit.setCurrentSection(edit.Section.YearSection)
    qtbot.keyClick(edit, Qt.Key.Key_Up)
    assert edit.date().year() == year + 1


def test_calendar_add_icon_matches_its_text_colour_in_every_state(qtbot, session):
    """The Add icon is the theme's text colour, and white whenever the button is the blue default."""
    from project_scheduler.ui.theme import theme_manager

    def icon_colour(button):
        button.grab()  # the icon is chosen when the button is drawn
        image = button.icon().pixmap(24, 24).toImage()
        return next(image.pixelColor(x, y).name() for y in range(24) for x in range(24)
                    if image.pixelColor(x, y).alpha() == 255)

    for theme, text_colour in (("light", "#1e2533"), ("dark", "#e4e7ee")):
        theme_manager.apply(theme)
        dialog, _ = make_calendar_dialog(qtbot, session)
        add = dialog.add_holiday_button
        for blue in (False, True, False):  # both states, and back again
            add.setDefault(blue)
            assert add.isDefault() == blue
            assert icon_colour(add) == ("#ffffff" if blue else text_colour), (theme, blue)
        qtbot.mouseClick(add, Qt.MouseButton.LeftButton)  # however it gets there, the icon follows
        assert icon_colour(add) == ("#ffffff" if add.isDefault() else text_colour)
        dialog.reject()
