from datetime import date

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QApplication

from project_scheduler.ui.formatting import to_qdate
from project_scheduler.ui.task_dialog import TaskDialog
from project_scheduler.ui.task_model import Column


def test_switching_to_german_retranslates_menus_and_cells(window, qtbot):
    window.load_sample(1000)
    start = window.proxy.index(0, Column.START)
    english = start.data()
    assert window.file_menu.title() == "&File"

    window.set_language("de")
    qtbot.waitUntil(lambda: window.file_menu.title() == "&Datei")
    assert window.settings.language == "de"
    german_date = QLocale("de_DE").toString(to_qdate(date(2026, 1, 5)), QLocale.FormatType.ShortFormat)
    assert start.data() == german_date != english
    assert window.tasks_card.value.text() == "1.000"
    assert window.model.headerData(Column.START, Qt.Orientation.Horizontal) == "Beginn"
    assert window.language_actions["de"].isChecked()

    window.set_language("en")
    qtbot.waitUntil(lambda: window.file_menu.title() == "&File")
    assert start.data() == english


def test_switching_to_japanese(window, qtbot):
    window.set_language("ja")
    qtbot.waitUntil(lambda: window.file_menu.title() == "ファイル(&F)")
    assert window.app_title.text() == "プロジェクトスケジューラー"
    assert window.windowTitle().endswith("— プロジェクトスケジューラー")


def test_app_name_is_translated_in_german(window, qtbot):
    window.set_language("de")
    qtbot.waitUntil(lambda: window.app_title.text() == "Projektplaner")
    assert window.windowTitle().endswith("— Projektplaner")


def test_untitled_is_translated_for_an_unsaved_project(window, qtbot):
    assert window.file_path is None
    assert window.windowTitle().startswith("Untitled")
    window.set_language("de")
    qtbot.waitUntil(lambda: window.file_label.text() == "Unbenannt")
    assert window.windowTitle().startswith("Unbenannt")
    window.set_language("ja")
    qtbot.waitUntil(lambda: window.file_label.text() == "無題")
    assert window.windowTitle().startswith("無題")
    window.load_sample(100)  # a fresh unsaved project keeps the translated name
    assert window.file_label.text() == "無題"


def test_open_dialog_retranslates(window, qtbot):
    dialog = window.add_task()
    assert dialog.windowTitle() == "New task"
    window.set_language("de")
    qtbot.waitUntil(lambda: dialog.windowTitle() == "Neue Aufgabe")
    assert isinstance(dialog, TaskDialog)
    dialog.reject()


def test_error_messages_are_translated(window):
    window.set_language("de")
    window.proxy.setData(window.proxy.index(0, Column.NAME), " ")
    assert window.statusBar().currentMessage() == "Der Aufgabenname darf nicht leer sein."


def test_switching_theme_changes_stylesheet(window):
    app = QApplication.instance()
    light = app.styleSheet()
    assert "light theme" in light
    window.set_theme("dark")
    dark = app.styleSheet()
    assert dark != light and "dark theme" in dark
    assert window.settings.theme == "dark"
    assert window.theme_actions["dark"].isChecked()


def test_theme_updates_table_palette(window):
    row = next(r for r in range(window.proxy.rowCount()) if window.proxy.index(r, Column.CRITICAL).data())
    light = window.proxy.index(row, Column.NAME).data(Qt.ItemDataRole.BackgroundRole)
    window.set_theme("dark")
    dark = window.proxy.index(row, Column.NAME).data(Qt.ItemDataRole.BackgroundRole)
    assert light != dark


def _toolbar_buttons(window):
    return [window.toolbar.widgetForAction(a) for a in window.toolbar.actions() if not a.isSeparator()]


def test_toolbar_keeps_every_button_visible_after_language_change(window, qtbot):
    """German labels are longer; no button (Calendar is last) may drop into the overflow menu."""
    window.resize(1280, 780)
    for code, calendar_label in (("de", "Kalender"), ("ja", "カレンダー"), ("en", "Calendar")):
        window.set_language(code)
        qtbot.waitUntil(lambda: window.toolbar.widgetForAction(window.calendar_action).text() == calendar_label)
        qtbot.waitUntil(lambda: all(b.isVisible() for b in _toolbar_buttons(window)))
        assert window.toolbar.sizeHint().width() <= window.width()


def test_window_cannot_shrink_below_the_labelled_toolbar(window, qtbot):
    from PySide6.QtCore import Qt

    for code, calendar_label in (("de", "Kalender"), ("ja", "カレンダー"), ("en", "Calendar")):
        window.set_language(code)
        qtbot.waitUntil(lambda: window.calendar_action.iconText() == calendar_label)
        assert window.minimumWidth() >= window.toolbar.sizeHint().width()
        window.resize(400, 600)  # clamped to the minimum
        qtbot.waitUntil(lambda: window.width() == window.minimumWidth())
        assert window.toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        qtbot.waitUntil(lambda: all(b.isVisible() for b in _toolbar_buttons(window)))


def test_toolbar_labels_use_full_menu_wording_without_mnemonics(window, qtbot):
    assert window.add_action.iconText() == "Add task"
    assert window.new_action.iconText() == "New project"
    window.set_language("ja")
    qtbot.waitUntil(lambda: window.add_action.iconText() == "タスクを追加")  # no "(&A)" or "…"
    assert window.calendar_action.iconText() == "カレンダー"


def test_ok_buttons_are_translated(window, qtbot):
    task_dialog = window.add_task()
    calendar_dialog = window.edit_calendar()
    assert task_dialog.ok_button.text() == calendar_dialog.ok_button.text() == "OK"
    for code, ok in (("de", "Bestätigen"), ("ja", "決定"), ("en", "OK")):
        window.set_language(code)
        qtbot.waitUntil(lambda: task_dialog.ok_button.text() == ok)
        qtbot.waitUntil(lambda: calendar_dialog.ok_button.text() == ok)
    task_dialog.reject()
    calendar_dialog.reject()


def test_name_column_and_label_are_translated_in_german(window, qtbot):
    window.set_language("de")
    qtbot.waitUntil(lambda: window.model.headerData(Column.NAME, Qt.Orientation.Horizontal) == "Aufgabenname")
    dialog = window.add_task()
    assert dialog.name_label.text() == "&Aufgabenname:"
    dialog.reject()


def test_language_menu_names_are_translated_with_native_names(window, qtbot):
    names = lambda: [window.language_actions[c].text() for c in ("en", "de", "ja")]
    assert names() == ["English", "German (Deutsch)", "Japanese (日本語)"]
    window.set_language("de")
    qtbot.waitUntil(lambda: names() == ["Englisch (English)", "Deutsch", "Japanisch (日本語)"])
    window.set_language("ja")
    qtbot.waitUntil(lambda: names() == ["英語（English）", "ドイツ語（Deutsch）", "日本語"])
    assert window.language_actions["ja"].isChecked()


def test_application_display_name_is_translated(window, qtbot):
    app = QApplication.instance()
    assert app.applicationDisplayName() == "Project Scheduler"
    window.set_language("de")
    qtbot.waitUntil(lambda: app.applicationDisplayName() == "Projektplaner")
    window.set_language("ja")
    qtbot.waitUntil(lambda: app.applicationDisplayName() == "プロジェクトスケジューラー")


def test_date_picker_popup_follows_the_theme(window, qtbot):
    """The calendar popup must not keep a white background (dates looked disabled in dark)."""
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QAbstractItemView

    def popup_colors():
        dialog = window.edit_calendar()
        view = dialog.start_edit.calendarWidget().findChild(QAbstractItemView)
        view.ensurePolished()
        colors = (view.palette().color(QPalette.ColorRole.Base), view.palette().color(QPalette.ColorRole.Text))
        dialog.reject()
        return colors

    light_base, light_text = popup_colors()
    assert light_base.lightness() > 200 and light_text.lightness() < 100
    window.set_theme("dark")
    dark_base, dark_text = popup_colors()
    assert dark_base.lightness() < 60 and dark_text.lightness() > 180  # light text on dark, readable
