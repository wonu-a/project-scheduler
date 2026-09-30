"""Every window and dialog opened the way a user opens it, answered by clicking its buttons."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QFileDialog, QMessageBox

from project_scheduler.ui.calendar_dialog import CalendarDialog
from project_scheduler.ui.task_dialog import TaskDialog
from project_scheduler.ui.task_model import Column


def make_dirty(window):
    window.proxy.setData(window.proxy.index(0, Column.DURATION), 9, Qt.ItemDataRole.EditRole)
    assert not window.undo_stack.isClean()


def click(qtbot, button):
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


# --- calendar dialog through the menu/toolbar action ----------------------------------------

def test_calendar_opens_from_its_action_and_cancel_button_changes_nothing(window, qtbot):
    window.calendar_action.trigger()
    dialog = window.findChild(CalendarDialog)
    assert dialog is not None
    qtbot.waitUntil(dialog.isVisible)
    dialog.weekday_boxes[0].setChecked(False)
    click(qtbot, dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))
    qtbot.waitUntil(lambda: not dialog.isVisible())
    assert window.undo_stack.count() == 0
    assert 0 in window.session.project.calendar.working_weekdays


def test_calendar_opened_from_its_action_ok_button_applies(window, qtbot):
    window.calendar_action.trigger()
    dialog = window.findChild(CalendarDialog)
    qtbot.waitUntil(dialog.isVisible)
    click(qtbot, dialog.weekday_boxes[4])  # untick Friday with a real click
    click(qtbot, dialog.ok_button)
    qtbot.waitUntil(lambda: not dialog.isVisible())
    assert 4 not in window.session.project.calendar.working_weekdays
    assert window.undo_stack.count() == 1


# --- task dialog through the Edit action ----------------------------------------------------

def test_edit_task_opens_from_its_action_and_ok_applies(window, qtbot):
    window.table.selectRow(1)
    window.edit_action.trigger()
    dialog = window.findChild(TaskDialog)
    qtbot.waitUntil(dialog.isVisible)
    assert dialog.name_edit.text() == "Build"
    dialog.name_edit.clear()
    qtbot.keyClicks(dialog.name_edit, "Build v2")
    click(qtbot, dialog.ok_button)
    qtbot.waitUntil(lambda: not dialog.isVisible())
    assert window.session.project.find(2).name == "Build v2"
    window.undo_action.trigger()
    assert window.session.project.find(2).name == "Build"


def test_edit_task_cancel_button_changes_nothing(window, qtbot):
    window.table.selectRow(1)
    window.edit_action.trigger()
    dialog = window.findChild(TaskDialog)
    qtbot.waitUntil(dialog.isVisible)
    qtbot.keyClicks(dialog.name_edit, " changed")
    click(qtbot, dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))
    qtbot.waitUntil(lambda: not dialog.isVisible())
    assert window.session.project.find(2).name == "Build"
    assert window.undo_stack.count() == 0


# --- information / warning message box ------------------------------------------------------

def test_message_box_ok_button_closes_it(window, qtbot, tmp_path):
    bad = tmp_path / "bad.schedule.json"
    bad.write_text("{not json")
    window.open_path(bad)
    box = window.findChild(QMessageBox)
    qtbot.waitUntil(box.isVisible)
    assert "bad.schedule.json" in box.text()
    click(qtbot, box.button(QMessageBox.StandardButton.Ok))
    qtbot.waitUntil(lambda: window.findChild(QMessageBox) is None)  # closed and deleted


def test_message_box_ok_button_is_translated(window, qtbot, tmp_path):
    window.set_language("de")
    qtbot.waitUntil(lambda: window.file_menu.title() == "&Datei")
    bad = tmp_path / "bad.schedule.json"
    bad.write_text("{not json")
    window.open_path(bad)
    box = window.findChild(QMessageBox)
    assert box.button(QMessageBox.StandardButton.Ok).text() == "Bestätigen"
    click(qtbot, box.button(QMessageBox.StandardButton.Ok))


# --- the real "Unsaved changes?" prompt -----------------------------------------------------

def test_unsaved_changes_prompt_cancel_keeps_the_project(window, answer_modal):
    make_dirty(window)
    seen = {}

    def read_then_cancel(box):
        seen.update(kind=type(box), text=box.text())
        box.button(QMessageBox.StandardButton.Cancel).click()

    answered = answer_modal(read_then_cancel)
    window.new_project()
    assert len(answered) == 1 and seen["kind"] is QMessageBox
    assert seen["text"] == "Untitled has unsaved changes. Save them first?"
    assert window.proxy.rowCount() == 4
    assert window.isWindowModified()


def test_unsaved_changes_prompt_discard_continues(window, answer_modal):
    make_dirty(window)
    answer_modal(lambda box: box.button(QMessageBox.StandardButton.Discard).click())
    window.new_project()
    assert window.proxy.rowCount() == 0
    assert not window.isWindowModified()


def test_unsaved_changes_prompt_save_saves_then_continues(window, answer_modal, tmp_path):
    path = tmp_path / "plan.schedule.json"
    window.save_to(path)
    make_dirty(window)
    answer_modal(lambda box: box.button(QMessageBox.StandardButton.Save).click())
    window.new_project()
    assert window.proxy.rowCount() == 0
    saved = window.open_path(path).project
    assert saved.tasks[0].duration == 9  # the unsaved edit was written before continuing


def test_closing_with_unsaved_changes_prompts_and_cancel_keeps_window_open(window, answer_modal):
    make_dirty(window)
    answered = answer_modal(lambda box: box.button(QMessageBox.StandardButton.Cancel).click())
    assert not window.close()
    assert len(answered) == 1
    assert window.isVisible()


def test_unsaved_changes_prompt_buttons_are_translated(window, qtbot, answer_modal):
    window.set_language("de")
    qtbot.waitUntil(lambda: window.file_menu.title() == "&Datei")
    make_dirty(window)
    texts = {}

    def read_then_cancel(box):
        # (macOS ignores a message box's window title, so the text carries the message.)
        texts["text"] = box.text()
        texts["buttons"] = {b.text() for b in box.buttons()}
        box.button(QMessageBox.StandardButton.Cancel).click()

    answer_modal(read_then_cancel)
    window.new_project()
    assert texts["text"] == "Unbenannt enthält nicht gespeicherte Änderungen. Zuerst speichern?"
    assert texts["buttons"] == {"Speichern", "Verwerfen", "Abbrechen"}  # Qt's own German


# --- Open / Save file dialogs ---------------------------------------------------------------

def choose_file(path, seen):
    def answer(dialog):
        seen.update(kind=type(dialog), file_mode=dialog.fileMode(), accept_mode=dialog.acceptMode())
        dialog.selectFile(str(path))
        dialog.accept()
    return answer


def test_open_action_opens_file_dialog_and_loads_the_chosen_file(window, answer_modal, tmp_path):
    path = tmp_path / "chosen.schedule.json"
    window.save_to(path)
    window.new_project()
    seen = {}
    answered = answer_modal(choose_file(path, seen))
    window.open_action.trigger()
    assert len(answered) == 1 and seen["kind"] is QFileDialog
    assert seen["file_mode"] == QFileDialog.FileMode.ExistingFile
    assert window.file_path == path
    assert window.proxy.rowCount() == 4


def test_open_file_dialog_cancel_changes_nothing(window, answer_modal):
    answer_modal(lambda dialog: dialog.reject())
    window.open_action.trigger()
    assert window.file_path is None
    assert window.proxy.rowCount() == 4


def test_save_action_on_new_project_asks_for_a_file_name(window, answer_modal, tmp_path):
    make_dirty(window)
    seen = {}
    answer_modal(choose_file(tmp_path / "plan", seen))
    window.save_action.trigger()
    assert seen["kind"] is QFileDialog and seen["accept_mode"] == QFileDialog.AcceptMode.AcceptSave
    assert window.file_path == tmp_path / "plan.schedule.json"  # suffix added
    assert window.file_path.exists()
    assert not window.isWindowModified()


def test_save_file_dialog_cancel_saves_nothing(window, answer_modal, tmp_path):
    make_dirty(window)
    answer_modal(lambda dialog: dialog.reject())
    window.save_as_action.trigger()
    assert window.file_path is None
    assert window.isWindowModified()
    assert not list(tmp_path.glob("*.schedule.json"))
