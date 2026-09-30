"""The main window: header bar, toolbar, filterable task table, menus."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from PySide6.QtCore import QEvent, QLocale, QModelIndex, QObject, QSize, QSortFilterProxyModel, Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QIcon, QKeySequence, QShowEvent, QUndoStack
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import storage
from ..domain import Project, ValidationError
from ..samples import SAMPLE_SIZES, generate_sample
from .calendar_dialog import CalendarDialog
from .commands import DeleteTasksCommand, EditTaskCommand
from .errors import error_text, load_message, save_failed_text
from .formatting import format_date, format_number
from .i18n import LANGUAGES, NATIVE_NAMES, language_manager
from .session import ProjectSession
from .settings import AppSettings
from .task_dialog import TaskDialog
from .task_model import SORT_ROLE, Column, TaskTableModel
from .theme import THEMES, theme_manager

FILE_SUFFIX = ".schedule.json"
_COLUMN_WIDTHS = {
    Column.ID: 64, Column.NAME: 260, Column.DURATION: 120, Column.PREDECESSORS: 140,
    Column.START: 124, Column.FINISH: 124, Column.LATE_START: 136, Column.LATE_FINISH: 136,
    Column.SLACK: 100, Column.CRITICAL: 120,
}
_MIN_NAME_WIDTH = 160  # when Name fills the spare width automatically, it never gets narrower than this


def _plain_menu_text(text: str) -> str:
    """Menu text without its mnemonic ("&Save", "保存(&S)") or trailing ellipsis, for tooltips."""
    return re.sub(r"\(&.\)", "", text).replace("&", "").rstrip("…").strip()


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StatCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.value = QLabel(objectName="statValue")
        self.caption = QLabel(objectName="statCaption")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(0)
        layout.addWidget(self.value)
        layout.addWidget(self.caption)


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, project: Project | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mainWindow")
        self.setWindowIcon(QIcon(":/icons/app.svg"))
        self.settings = settings
        self.file_path: Path | None = None
        self._open_dialogs: list[QWidget] = []

        self.session = ProjectSession(project or Project.new(date.today()), self)
        self.undo_stack = QUndoStack(self)
        self.model = TaskTableModel(self.session, self)
        self.model.edit_handler = self._handle_cell_edit
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(SORT_ROLE)
        self.proxy.setFilterKeyColumn(Column.NAME)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self._action_icons: dict[QAction, str] = {}
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_central()
        self.statusBar().setObjectName("statusBar")

        self.undo_stack.cleanChanged.connect(self._update_title)
        self.undo_stack.canUndoChanged.connect(self.undo_action.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.redo_action.setEnabled)
        self.session.scheduleChanged.connect(self._update_header)
        self.session.reset.connect(self._update_header)
        self.table.selectionModel().selectionChanged.connect(self._update_actions)
        self.proxy.rowsRemoved.connect(self._update_actions)
        self.proxy.modelReset.connect(self._update_actions)
        language_manager.languageChanged.connect(self._sync_view_menu)
        theme_manager.themeChanged.connect(self._sync_view_menu)
        theme_manager.themeChanged.connect(self._refresh_icons)

        self.resize(1280, 780)
        self.retranslate_ui()
        self._update_actions()
        self._sync_view_menu()

    # --- construction -----------------------------------------------------------------------

    def _action(self, icon: str | None = None, slot=None, shortcut=None) -> QAction:
        action = QAction(theme_manager.icon(icon) if icon else QIcon(), "", self)
        if icon:
            self._action_icons[action] = icon  # re-fetched on theme change (per-theme icons)
        if slot is not None:
            action.triggered.connect(slot)
        if shortcut is not None:
            if isinstance(shortcut, list):
                action.setShortcuts(shortcut)
            else:
                action.setShortcut(shortcut)
        return action

    def _create_actions(self) -> None:
        K = QKeySequence.StandardKey
        self.new_action = self._action("new", self.new_project, K.New)
        self.open_action = self._action("open", self.open_file, K.Open)
        self.save_action = self._action("save", self.save, K.Save)
        self.save_as_action = self._action(None, self.save_as, K.SaveAs)
        self.quit_action = self._action(None, self.close, K.Quit)
        self.undo_action = self._action("undo", self.undo_stack.undo, K.Undo)
        # Ctrl+Shift+Z and Ctrl+Y everywhere; some platforms already include them in StandardKey.Redo,
        # and a duplicate would make the shortcut ambiguous.
        redo_keys = QKeySequence.keyBindings(K.Redo)
        for extra in (QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")):
            if extra not in redo_keys:
                redo_keys.append(extra)
        self.redo_action = self._action("redo", self.undo_stack.redo, redo_keys)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self.add_action = self._action("add", self.add_task, QKeySequence("Ctrl+T"))
        # A lambda, because triggered(bool) would otherwise pass False as edit_task's task_id.
        self.edit_action = self._action("edit", lambda: self.edit_task(), QKeySequence("Ctrl+E"))
        self.delete_action = self._action("delete", self.delete_tasks, [QKeySequence(K.Delete), QKeySequence("Backspace")])
        self.calendar_action = self._action("calendar", self.edit_calendar)

        self.sample_actions: dict[int, QAction] = {}
        for size in SAMPLE_SIZES:
            self.sample_actions[size] = self._action(None, lambda _=False, s=size: self.load_sample(s))

        self.theme_group = QActionGroup(self)
        self.theme_actions: dict[str, QAction] = {}
        for name in THEMES:
            action = self._action(None, lambda _=False, n=name: self.set_theme(n))
            action.setCheckable(True)
            self.theme_group.addAction(action)
            self.theme_actions[name] = action

        self.language_group = QActionGroup(self)
        self.language_actions: dict[str, QAction] = {}
        for code in LANGUAGES:
            action = self._action(None, lambda _=False, c=code: self.set_language(c))
            action.setCheckable(True)
            self.language_group.addAction(action)
            self.language_actions[code] = action

    def _create_menus(self) -> None:
        bar = self.menuBar()
        self.file_menu = bar.addMenu("")
        self.file_menu.addActions([self.new_action, self.open_action])
        self.recent_menu = self.file_menu.addMenu("")
        self.recent_menu.aboutToShow.connect(self._rebuild_recent_menu)
        self.sample_menu = self.file_menu.addMenu("")
        self.sample_menu.addActions(list(self.sample_actions.values()))
        self.file_menu.addSeparator()
        self.file_menu.addActions([self.save_action, self.save_as_action])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.quit_action)

        self.edit_menu = bar.addMenu("")
        self.edit_menu.addActions([self.undo_action, self.redo_action])
        self.edit_menu.addSeparator()
        self.edit_menu.addActions([self.add_action, self.edit_action, self.delete_action])

        self.project_menu = bar.addMenu("")
        self.project_menu.addAction(self.calendar_action)

        self.view_menu = bar.addMenu("")
        self.theme_menu = self.view_menu.addMenu("")
        self.theme_menu.addActions(list(self.theme_actions.values()))
        self.language_menu = self.view_menu.addMenu("")
        self.language_menu.addActions(list(self.language_actions.values()))

    def _create_toolbar(self) -> None:
        self.toolbar = QToolBar(objectName="mainToolBar")
        self.toolbar.setMovable(False)
        # Smaller than the macOS default so the labelled toolbar fits in German at the default window size.
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toolbar.addActions([self.new_action, self.open_action, self.save_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.add_action, self.edit_action, self.delete_action])
        self.toolbar.addSeparator()
        self.toolbar.addActions([self.undo_action, self.redo_action])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.calendar_action)
        self.addToolBar(self.toolbar)
    def _fit_window_to_toolbar(self) -> None:
        """The window can't get narrower than the full toolbar, so no button drops into the overflow menu.

        The width depends on the language (German labels are longest), so this runs on every change.
        """
        for action in self.toolbar.actions():
            button = self.toolbar.widgetForAction(action)
            if button is not None:
                button.ensurePolished()
        self.toolbar.layout().invalidate()
        self.setMinimumWidth(self.toolbar.sizeHint().width())

    def _on_section_resized(self, index: int, _old: int, _new: int) -> None:
        if index == Column.NAME and not self._fitting_name_column:
            self._name_width_user_set = True  # the user dragged it; keep their width from now on

    def _fit_name_column(self) -> None:
        if self._name_width_user_set:
            return
        others = sum(width for column, width in _COLUMN_WIDTHS.items() if column != Column.NAME)
        width = max(_MIN_NAME_WIDTH, self.table.viewport().width() - others)
        self._fitting_name_column = True
        self.table.setColumnWidth(Column.NAME, width)
        self._fitting_name_column = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.table.viewport() and event.type() == QEvent.Type.Resize:
            self._fit_name_column()
        return super().eventFilter(watched, event)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._fit_window_to_toolbar()  # buttons are fully styled only once shown

    def _create_central(self) -> None:
        central = QWidget(objectName="centralArea")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header bar: app identity on the left, project statistics on the right.
        self.header = QFrame(objectName="headerBar")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(12)
        icon = QLabel(objectName="appIcon")
        icon.setPixmap(QIcon(":/icons/app.svg").pixmap(36, 36))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.app_title = QLabel(objectName="appTitle")
        self.file_label = QLabel(objectName="fileLabel")
        titles.addWidget(self.app_title)
        titles.addWidget(self.file_label)
        header_layout.addWidget(icon)
        header_layout.addLayout(titles)
        header_layout.addStretch(1)
        self.tasks_card = StatCard()
        self.finish_card = StatCard()
        self.critical_card = StatCard()
        for card in (self.tasks_card, self.finish_card, self.critical_card):
            header_layout.addWidget(card)
        outer.addWidget(self.header)

        content = QWidget(objectName="contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)
        filter_row = QHBoxLayout()
        self.filter_edit = QLineEdit(objectName="filterEdit")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.addAction(QIcon(":/icons/search.svg"), QLineEdit.ActionPosition.LeadingPosition)
        self.filter_edit.textChanged.connect(self.proxy.setFilterFixedString)
        self.legend_label = QLabel(objectName="legendLabel")
        self.legend_badge = QLabel(objectName="criticalBadge")
        self.legend_badge.setProperty("critical", True)
        self.filter_edit.setMaximumWidth(420)
        filter_row.addWidget(self.filter_edit)
        filter_row.addStretch(1)
        filter_row.addWidget(self.legend_badge)
        filter_row.addWidget(self.legend_label)
        content_layout.addLayout(filter_row)

        self.table = QTableView(objectName="taskTable")
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(Column.ID, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(32)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for column, width in _COLUMN_WIDTHS.items():
            self.table.setColumnWidth(column, width)
        # Every column, Name included, can be resized by dragging; the last one takes up any spare width.
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        # Until the user drags it, Name absorbs the spare width so the table fits without scrolling.
        self._name_width_user_set = False
        self._fitting_name_column = False
        header.sectionResized.connect(self._on_section_resized)
        self.table.viewport().installEventFilter(self)
        self.table.doubleClicked.connect(self._on_double_clicked)
        content_layout.addWidget(self.table, 1)
        outer.addWidget(content, 1)
        self.setCentralWidget(central)

    # --- translation ------------------------------------------------------------------------

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self) -> None:
        self.file_menu.setTitle(self.tr("&File"))
        self.edit_menu.setTitle(self.tr("&Edit"))
        self.project_menu.setTitle(self.tr("&Project"))
        self.view_menu.setTitle(self.tr("&View"))
        self.recent_menu.setTitle(self.tr("Open &recent"))
        self.sample_menu.setTitle(self.tr("Load &sample project"))
        self.theme_menu.setTitle(self.tr("&Theme"))
        self.language_menu.setTitle(self.tr("&Language"))

        self.new_action.setText(self.tr("&New project"))
        self.open_action.setText(self.tr("&Open…"))
        self.save_action.setText(self.tr("&Save"))
        self.save_as_action.setText(self.tr("Save &as…"))
        self.quit_action.setText(self.tr("&Quit"))
        self.undo_action.setText(self.tr("&Undo"))
        self.redo_action.setText(self.tr("&Redo"))
        self.add_action.setText(self.tr("&Add task…"))
        self.edit_action.setText(self.tr("&Edit task…"))
        self.delete_action.setText(self.tr("&Delete"))
        self.calendar_action.setText(self.tr("&Calendar…"))
        for size, action in self.sample_actions.items():
            action.setText(self.tr("{0} tasks").format(format_number(size)))
        self.theme_actions["light"].setText(self.tr("&Light"))
        self.theme_actions["dark"].setText(self.tr("&Dark"))
        translated_names = {"en": self.tr("English"), "de": self.tr("German"), "ja": self.tr("Japanese")}
        for code, action in self.language_actions.items():
            name, native = translated_names[code], NATIVE_NAMES[code]
            # "Englisch (English)"; just "Deutsch" when both names are the same.
            action.setText(name if name == native else self.tr("{0} ({1})").format(name, native))
        self.toolbar.setWindowTitle(self.tr("Toolbar"))
        # Toolbar buttons show the menu wording without its mnemonic ("タスクを追加(&A)…" -> "タスクを追加").
        for action in self.toolbar.actions():
            if not action.isSeparator():
                action.setIconText(_plain_menu_text(action.text()))
                action.setToolTip(action.iconText())
        self._fit_window_to_toolbar()

        self.app_title.setText(self.tr("Project Scheduler"))
        # macOS shows the display name in the application menu, so it is translated too.
        QApplication.instance().setApplicationDisplayName(self.tr("Project Scheduler"))
        self.tasks_card.caption.setText(self.tr("Tasks"))
        self.finish_card.caption.setText(self.tr("Project finish"))
        self.critical_card.caption.setText(self.tr("Critical tasks"))
        self.filter_edit.setPlaceholderText(self.tr("Filter tasks by name…"))
        self.legend_badge.setText(self.tr("Critical"))
        self.legend_label.setText(self.tr("Zero slack: any delay moves the project finish."))
        self._update_title()
        self._update_header()

    # --- display ----------------------------------------------------------------------------

    def _document_name(self) -> str:
        return self.file_path.name if self.file_path else self.tr("Untitled")

    def _update_title(self, *_args) -> None:
        name = self._document_name()
        self.setWindowTitle(self.tr("{0}[*] — Project Scheduler").format(name))
        self.setWindowModified(not self.undo_stack.isClean())
        self.file_label.setText(str(self.file_path) if self.file_path else name)

    def _update_header(self) -> None:
        schedule = self.session.schedule
        self.tasks_card.value.setText(format_number(len(self.session.project.tasks)))
        finish = schedule.project_finish_date()
        self.finish_card.value.setText(format_date(finish) if finish else self.tr("—"))
        critical = schedule.critical_count
        self.critical_card.value.setText(format_number(critical))
        self.critical_card.setProperty("critical", critical > 0)
        _repolish(self.critical_card)
        for label in (self.critical_card.value, self.critical_card.caption):
            _repolish(label)

    def _selected_task_ids(self) -> list[int]:
        rows = self.table.selectionModel().selectedRows()
        return [self.model.task_id_at(self.proxy.mapToSource(i).row()) for i in rows]

    def _update_actions(self, *_args) -> None:
        count = len(self.table.selectionModel().selectedRows())
        self.edit_action.setEnabled(count == 1)
        self.delete_action.setEnabled(count > 0)

    def _refresh_icons(self, *_args) -> None:
        for action, name in self._action_icons.items():
            action.setIcon(theme_manager.icon(name))

    def _sync_view_menu(self, *_args) -> None:
        self.theme_actions[theme_manager.name].setChecked(True)
        self.language_actions[language_manager.code].setChecked(True)

    def show_message(self, text: str, warning: bool = False) -> None:
        """Non-blocking message box, so tests and the event loop are never stalled."""
        box = QMessageBox(
            QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Information,
            self.tr("Project Scheduler"), text, QMessageBox.StandardButton.Ok, self,
        )
        box.button(QMessageBox.StandardButton.Ok).setText(self.tr("OK"))
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.open()

    # --- project lifecycle ------------------------------------------------------------------

    def _set_project(self, project: Project, path: Path | None) -> None:
        self.session.replace_project(project)
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.file_path = path
        self.settings.last_file = str(path) if path else ""
        if path:
            self.settings.add_recent_file(str(path))
        self._update_title()
        self._update_actions()

    def confirm_discard(self) -> bool:
        """Ask before throwing away unsaved changes. Returns True if it is OK to continue."""
        if self.undo_stack.isClean():
            return True
        answer = QMessageBox.question(
            self, self.tr("Unsaved changes"),
            self.tr("{0} has unsaved changes. Save them first?").format(self._document_name()),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if self.confirm_discard():
            self._set_project(Project.new(date.today()), None)

    def load_sample(self, size: int) -> None:
        if self.confirm_discard():
            self._set_project(generate_sample(size), None)
            self.statusBar().showMessage(
                self.tr("Loaded a sample project with {0} tasks.").format(format_number(size)), 5000
            )

    def open_file(self) -> None:
        if not self.confirm_discard():
            return
        start_dir = str(self.file_path.parent) if self.file_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open project"), start_dir, self.tr("Schedules (*.schedule.json);;All files (*)")
        )
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path, *, quiet_if_missing: bool = False) -> storage.LoadResult:
        result = storage.load(path)
        if result.status in (storage.LoadStatus.OK, storage.LoadStatus.MIGRATED):
            self._set_project(result.project, path)
        else:
            self._set_project(result.project, None)
            if result.status is storage.LoadStatus.MISSING:
                self.settings.remove_recent_file(str(path))
        if result.message_code is not storage.MessageCode.NONE:
            if not (quiet_if_missing and result.status is storage.LoadStatus.MISSING):
                self.show_message(
                    load_message(result.message_code, path, result.backup_path),
                    warning=result.status is not storage.LoadStatus.MIGRATED,
                )
        return result

    def save(self) -> bool:
        if self.file_path is None:
            return self.save_as()
        return self.save_to(self.file_path)

    def save_as(self) -> bool:
        start = str(self.file_path) if self.file_path else self.tr("Untitled") + FILE_SUFFIX
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save project"), start, self.tr("Schedules (*.schedule.json)")
        )
        if not path:
            return False
        if not path.endswith(FILE_SUFFIX):
            path += FILE_SUFFIX
        return self.save_to(Path(path))

    def save_to(self, path: Path) -> bool:
        try:
            storage.save(self.session.project, path)
        except OSError as exc:
            self.show_message(save_failed_text(path, exc.strerror or str(exc)), warning=True)
            return False
        self.file_path = path
        self.settings.last_file = str(path)
        self.settings.add_recent_file(str(path))
        self.undo_stack.setClean()
        self._update_title()
        self.statusBar().showMessage(self.tr("Saved {0}.").format(path.name), 4000)
        return True

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        files = self.settings.recent_files
        if not files:
            empty = self.recent_menu.addAction(self.tr("No recent files"))
            empty.setEnabled(False)
            return
        for file in files:
            action = self.recent_menu.addAction(Path(file).name)
            action.setToolTip(file)
            action.triggered.connect(lambda _=False, f=file: self._open_recent(f))

    def _open_recent(self, file: str) -> None:
        if self.confirm_discard():
            self.open_path(Path(file))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.confirm_discard():
            self.settings.sync()
            event.accept()
        else:
            event.ignore()

    # --- edits ------------------------------------------------------------------------------

    def _keep_dialog(self, dialog: QWidget) -> None:
        self._open_dialogs.append(dialog)
        dialog.finished.connect(lambda _r, d=dialog: self._open_dialogs.remove(d))
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()

    def add_task(self) -> TaskDialog:
        dialog = TaskDialog(self.session, self.undo_stack, None, self)
        self._keep_dialog(dialog)
        return dialog

    def edit_task(self, task_id: int | None = None) -> TaskDialog | None:
        if task_id is None:
            ids = self._selected_task_ids()
            if len(ids) != 1:
                return None
            task_id = ids[0]
        dialog = TaskDialog(self.session, self.undo_stack, task_id, self)
        self._keep_dialog(dialog)
        return dialog

    def edit_calendar(self) -> CalendarDialog:
        dialog = CalendarDialog(self.session, self.undo_stack, self)
        self._keep_dialog(dialog)
        return dialog

    def delete_tasks(self) -> None:
        command = DeleteTasksCommand.create(self.session, self._selected_task_ids())
        if isinstance(command, ValidationError):
            self.statusBar().showMessage(error_text(command, self.session.name_of), 6000)
        elif command is not None:
            self.undo_stack.push(command)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        if not self.proxy.flags(index) & Qt.ItemFlag.ItemIsEditable:
            self.edit_task(self.model.task_id_at(self.proxy.mapToSource(index).row()))

    def _handle_cell_edit(self, task_id: int, column: Column, value: object) -> bool:
        if column == Column.NAME:
            command = EditTaskCommand.create(self.session, task_id, name=str(value))
        else:
            duration = value
            if isinstance(value, str):
                ok_value, ok = QLocale().toInt(value)
                duration = ok_value if ok else value
            command = EditTaskCommand.create(self.session, task_id, duration=duration)
        if isinstance(command, ValidationError):
            self.statusBar().showMessage(error_text(command, self.session.name_of), 6000)
            return False
        if command is not None:
            self.undo_stack.push(command)
        return True

    # --- preferences ------------------------------------------------------------------------

    def set_theme(self, name: str) -> None:
        theme_manager.apply(name)
        self.settings.theme = theme_manager.name

    def set_language(self, code: str) -> None:
        language_manager.set_language(code)
        self.settings.language = language_manager.code
