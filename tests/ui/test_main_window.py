import json
from datetime import date

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QMessageBox

from project_scheduler.storage import LoadStatus
from project_scheduler.ui.formatting import to_qdate
from project_scheduler.ui.task_dialog import TaskDialog
from project_scheduler.ui.task_model import Column


def cell(window, row, column):
    return window.proxy.index(row, column)


def test_window_opens_with_project(window):
    assert window.isVisible()
    assert "Project Scheduler" in window.windowTitle()
    assert window.proxy.rowCount() == 4
    assert window.tasks_card.value.text() == "4"
    assert window.critical_card.property("critical") is True
    assert not window.isWindowModified()


def test_new_project_clears(window):
    window.new_project()
    assert window.proxy.rowCount() == 0


def test_new_project_cancelled_keeps_changes(window, monkeypatch):
    window.proxy.setData(cell(window, 0, Column.DURATION), 5, Qt.ItemDataRole.EditRole)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.new_project()
    assert window.proxy.rowCount() == 4
    assert window.isWindowModified()


def test_table_shows_schedule_dates(window):
    # Design: Fri Jan 2 - Tue Jan 6; Build: Wed Jan 7 - Thu Jan 8
    en = QLocale("en_US")
    assert cell(window, 1, Column.START).data() == en.toString(to_qdate(date(2026, 1, 7)), QLocale.FormatType.ShortFormat)
    assert cell(window, 1, Column.FINISH).data() == en.toString(to_qdate(date(2026, 1, 8)), QLocale.FormatType.ShortFormat)
    assert cell(window, 2, Column.SLACK).data() == "4"
    assert cell(window, 0, Column.CRITICAL).data() == "Critical"
    assert cell(window, 2, Column.CRITICAL).data() == ""


def test_inline_edit_pushes_command_and_marks_modified(window):
    assert window.proxy.setData(cell(window, 0, Column.DURATION), 5, Qt.ItemDataRole.EditRole)
    assert window.session.project.tasks[0].duration == 5
    assert window.undo_stack.count() == 1
    assert window.isWindowModified()
    assert window.windowTitle().startswith("Untitled")
    window.undo_stack.undo()
    assert not window.isWindowModified()


def test_invalid_inline_edit_is_rejected(window):
    assert not window.proxy.setData(cell(window, 0, Column.DURATION), 10_000, Qt.ItemDataRole.EditRole)
    assert not window.proxy.setData(cell(window, 0, Column.NAME), "   ", Qt.ItemDataRole.EditRole)
    assert window.undo_stack.count() == 0
    assert "duration" in window.statusBar().currentMessage() or "name" in window.statusBar().currentMessage()


def test_ctrl_z_undoes_through_the_ui(window, qtbot):
    window.proxy.setData(cell(window, 0, Column.NAME), "Renamed", Qt.ItemDataRole.EditRole)
    assert window.session.project.tasks[0].name == "Renamed"
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    qtbot.keyClick(window.table, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert window.session.project.tasks[0].name == "Design"
    qtbot.keyClick(window.table, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert window.session.project.tasks[0].name == "Renamed"


def test_delete_selected_rows_is_one_undo_step(window):
    window.table.selectRow(0)
    window.table.selectionModel().select(
        cell(window, 2, 0), window.table.selectionModel().SelectionFlag.Select | window.table.selectionModel().SelectionFlag.Rows
    )
    assert window.delete_action.isEnabled()
    window.delete_action.trigger()
    assert [t.id for t in window.session.project.tasks] == [2, 4]
    assert window.session.project.find(2).predecessors == []
    window.undo_action.trigger()
    assert [t.id for t in window.session.project.tasks] == [1, 2, 3, 4]
    assert window.session.project.find(4).predecessors == [2, 3]


def test_sort_and_filter(window):
    window.table.sortByColumn(Column.DURATION, Qt.SortOrder.DescendingOrder)
    assert cell(window, 0, Column.NAME).data() == "Design"
    window.filter_edit.setText("bu")
    assert window.proxy.rowCount() == 1
    assert cell(window, 0, Column.NAME).data() == "Build"


def test_load_sample_resets_and_is_clean(window):
    window.proxy.setData(cell(window, 0, Column.DURATION), 5, Qt.ItemDataRole.EditRole)
    window.undo_stack.setClean()
    window.load_sample(1000)
    assert window.proxy.rowCount() == 1000
    assert window.undo_stack.count() == 0
    assert window.undo_stack.isClean()
    assert window.tasks_card.value.text() == "1,000"


def test_save_and_open_round_trip(window, tmp_path):
    path = tmp_path / "plan.schedule.json"
    window.proxy.setData(cell(window, 0, Column.NAME), "Saved name", Qt.ItemDataRole.EditRole)
    assert window.save_to(path)
    assert window.undo_stack.isClean()
    assert "plan.schedule.json" in window.windowTitle()
    assert window.settings.recent_files == [str(path)]

    window.new_project()
    assert window.proxy.rowCount() == 0
    result = window.open_path(path)
    assert result.status is LoadStatus.OK
    assert window.session.project.tasks[0].name == "Saved name"
    assert window.file_path == path


def test_opening_corrupt_file_starts_empty_and_tells_user(window, tmp_path, qtbot):
    path = tmp_path / "bad.schedule.json"
    path.write_text(json.dumps({"format_version": 1, "project": []}))
    result = window.open_path(path)
    assert result.status is LoadStatus.CORRUPT
    assert window.proxy.rowCount() == 0
    assert window.file_path is None
    box = window.findChild(QMessageBox)
    assert box is not None and "bad.schedule.json" in box.text() and ".corrupt-" in box.text()
    box.close()


def test_missing_last_file_on_startup_is_quiet(window, tmp_path):
    result = window.open_path(tmp_path / "gone.schedule.json", quiet_if_missing=True)
    assert result.status is LoadStatus.MISSING
    assert window.findChild(QMessageBox) is None


def test_close_with_unsaved_changes_asks(window, monkeypatch):
    window.proxy.setData(cell(window, 0, Column.DURATION), 5, Qt.ItemDataRole.EditRole)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    assert not window.close()
    assert window.isVisible()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    assert window.close()


def test_add_action_opens_task_dialog(window, qtbot):
    window.add_action.trigger()
    dialog = window.findChild(TaskDialog)
    assert dialog is not None and dialog.isVisible()
    dialog.reject()


def test_edit_action_needs_single_selection(window):
    assert not window.edit_action.isEnabled()
    window.table.selectRow(1)
    assert window.edit_action.isEnabled()
    dialog = window.edit_task()
    assert dialog.name_edit.text() == "Build"
    dialog.reject()


def test_every_column_including_name_can_be_resized(window):
    from PySide6.QtWidgets import QHeaderView

    header = window.table.horizontalHeader()
    for column in Column:
        if column != Column.CRITICAL:  # the last column fills any spare width
            assert header.sectionResizeMode(column) == QHeaderView.ResizeMode.Interactive, column.name
    before = header.sectionSize(Column.NAME)
    header.resizeSection(Column.NAME, before + 80)
    assert header.sectionSize(Column.NAME) == before + 80
    assert header.stretchLastSection()


def test_name_column_fills_spare_width_until_user_resizes_it(window, qtbot):
    header = window.table.horizontalHeader()
    window.resize(1400, 780)
    qtbot.waitUntil(lambda: header.length() <= window.table.viewport().width() + 1)  # no horizontal scrolling
    wide = header.sectionSize(Column.NAME)
    window.resize(window.minimumWidth(), 780)
    qtbot.waitUntil(lambda: header.sectionSize(Column.NAME) < wide)  # Name gave up the space
    others = header.length() - header.sectionSize(Column.NAME)
    assert header.sectionSize(Column.NAME) == max(160, window.table.viewport().width() - others)

    header.resizeSection(Column.NAME, 333)  # as if the user dragged it
    window.resize(1400, 780)
    qtbot.waitUntil(lambda: window.width() == 1400)
    assert header.sectionSize(Column.NAME) == 333  # the user's width is kept


# --- task notes in the table ----------------------------------------------------------------

def test_name_cell_tooltip_shows_notes(window):
    from project_scheduler.ui.commands import EditNotesCommand

    name_cell = lambda: window.proxy.index(0, Column.NAME)
    assert name_cell().data(Qt.ItemDataRole.ToolTipRole) is None  # no note, no tooltip
    window.undo_stack.push(EditNotesCommand.create(window.session, 1, "Waiting on vendor"))
    assert name_cell().data(Qt.ItemDataRole.ToolTipRole) == "Waiting on vendor"
    window.undo_action.trigger()
    assert name_cell().data(Qt.ItemDataRole.ToolTipRole) is None


# --- critical-only filter -------------------------------------------------------------------

def visible_names(window):
    return sorted(window.proxy.index(r, Column.NAME).data() for r in range(window.proxy.rowCount()))


def test_critical_only_filter(window, qtbot):
    # Design (3d) -> Build (2d) -> Launch; Docs (1d) has slack, so it is not critical.
    assert visible_names(window) == ["Build", "Design", "Docs", "Launch"]
    qtbot.mouseClick(window.critical_only_check, Qt.MouseButton.LeftButton)
    assert window.critical_only_check.isChecked()
    assert visible_names(window) == ["Build", "Design", "Launch"]
    qtbot.mouseClick(window.critical_only_check, Qt.MouseButton.LeftButton)
    assert visible_names(window) == ["Build", "Design", "Docs", "Launch"]


def test_critical_only_combines_with_name_filter(window):
    window.critical_only_check.setChecked(True)
    window.filter_edit.setText("d")  # Design, Docs, Build contain "d"
    assert visible_names(window) == ["Build", "Design"]


def test_critical_only_follows_schedule_changes(window):
    window.critical_only_check.setChecked(True)
    # Docs becomes the longest path to Launch, so it turns critical and Build stops being critical.
    window.proxy.sourceModel().setData(window.model.index(2, Column.DURATION), 10, Qt.ItemDataRole.EditRole)
    assert visible_names(window) == ["Docs", "Launch"]
    window.undo_action.trigger()
    assert visible_names(window) == ["Build", "Design", "Launch"]
