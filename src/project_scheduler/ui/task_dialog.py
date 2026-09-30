"""Add or edit a task: name, duration, notes and predecessors."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSortFilterProxyModel, Qt
from PySide6.QtGui import QIcon, QUndoStack
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..domain import ValidationError
from ..domain.model import MAX_DURATION
from .commands import (
    AddDependencyCommand,
    AddTaskCommand,
    EditNotesCommand,
    EditTaskCommand,
    RemoveDependencyCommand,
    predecessor_changes,
)
from .errors import error_text
from .session import ProjectSession
from .sizing import fit_line_edit_to_placeholder, fit_spin_box_to_widest_value, reserve_wrapped_label_heights
from .task_model import PredecessorListModel


class TaskDialog(QDialog):
    def __init__(
        self, session: ProjectSession, undo_stack: QUndoStack, task_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("taskDialog")
        self.session = session
        self.undo_stack = undo_stack
        self.task_id = task_id
        task = session.project.find(task_id) if task_id is not None else None

        self.title_label = QLabel(objectName="dialogTitle")
        self.name_edit = QLineEdit(objectName="nameEdit")
        self.duration_spin = QSpinBox(objectName="durationSpin")
        self.duration_spin.setRange(0, MAX_DURATION)
        self.notes_edit = QPlainTextEdit(objectName="notesEdit")
        self.notes_edit.setTabChangesFocus(True)  # Tab moves on, as in the other fields
        self.notes_edit.setMinimumHeight(64)
        self.notes_edit.setMaximumHeight(96)
        self.filter_edit = QLineEdit(objectName="filterEdit")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.addAction(QIcon(":/icons/search.svg"), QLineEdit.ActionPosition.LeadingPosition)

        self.predecessors = PredecessorListModel(session, task_id, task.predecessors if task else [], self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.predecessors)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.filter_edit.textChanged.connect(self.proxy.setFilterFixedString)
        self.predecessor_view = QListView(objectName="predecessorList")
        self.predecessor_view.setModel(self.proxy)
        self.predecessor_view.setUniformItemSizes(True)

        self.error_label = QLabel(objectName="errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        # Our own OK button: a standard one gets Qt's text back on every language change.
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.buttons.addButton("", QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok_button.setDefault(True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.name_label = QLabel(buddy=self.name_edit)
        self.duration_label = QLabel(buddy=self.duration_spin)
        self.notes_label = QLabel(buddy=self.notes_edit)
        self.predecessors_label = QLabel(buddy=self.filter_edit)
        self.form = QFormLayout()
        # The macOS style defaults to FieldsStayAtSizeHint, which keeps the name field narrow and
        # cuts off its placeholder however wide the dialog is.
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.addRow(self.name_label, self.name_edit)
        self.form.addRow(self.duration_label, self.duration_spin)
        self.form.addRow(self.notes_label, self.notes_edit)
        self.form.addRow(self.predecessors_label, self.filter_edit)
        self.form.addRow(self.predecessor_view)
        # With no other tasks there is nothing to pick; an empty list box looks like a text field.
        self.no_predecessors_hint = QLabel(objectName="emptyHint")
        self.no_predecessors_hint.setWordWrap(True)
        has_candidates = self.predecessors.rowCount() > 0
        self.form.setRowVisible(self.filter_edit, has_candidates)
        self.form.setRowVisible(self.predecessor_view, has_candidates)
        self.no_predecessors_hint.setVisible(not has_candidates)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(self.title_label)
        layout.addLayout(self.form)
        layout.addWidget(self.no_predecessors_hint)
        layout.addWidget(self.error_label)
        if not has_candidates:
            layout.addStretch(1)
        layout.addWidget(self.buttons)

        if task:
            self.name_edit.setText(task.name)
            self.duration_spin.setValue(task.duration)
            self.notes_edit.setPlainText(task.notes)
        else:
            self.duration_spin.setValue(1)
        self.resize(460, 600 if has_candidates else 340)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.ok_button.setText(self.tr("OK"))
        editing = self.task_id is not None
        title = self.tr("Edit task") if editing else self.tr("New task")
        self.setWindowTitle(title)
        self.title_label.setText(title)
        self.name_label.setText(self.tr("&Name:"))
        self.duration_label.setText(self.tr("&Duration:"))
        self.notes_label.setText(self.tr("N&otes:"))
        self.notes_edit.setPlaceholderText(self.tr("Optional notes about this task"))
        self.predecessors_label.setText(self.tr("&Predecessors:"))
        self.duration_spin.setSuffix(self.tr(" working days"))
        self.name_edit.setPlaceholderText(self.tr("What needs to be done?"))
        self.filter_edit.setPlaceholderText(self.tr("Filter tasks…"))
        self.no_predecessors_hint.setText(
            self.tr("No other tasks yet. Once the project has more tasks, you can choose predecessors here.")
        )
        # The dialog's smallest size must still show every field's full text.
        fit_line_edit_to_placeholder(self.name_edit)
        fit_line_edit_to_placeholder(self.filter_edit)
        fit_spin_box_to_widest_value(self.duration_spin)
        self._reserve_label_heights()

    def _reserve_label_heights(self) -> None:
        reserve_wrapped_label_heights(self.layout(), [self.no_predecessors_hint, self.error_label])

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def show_error(self, error: ValidationError) -> None:
        self.error_label.setText(error_text(error, self.session.name_of))
        self.error_label.show()
        self._reserve_label_heights()

    def accept(self) -> None:
        name = self.name_edit.text()
        duration = self.duration_spin.value()
        preds = self.predecessors.checked_ids()
        notes = self.notes_edit.toPlainText()
        if self.task_id is None:
            command = AddTaskCommand.create(self.session, name, duration, preds, notes)
            if isinstance(command, ValidationError):
                self.show_error(command)
                return
            self.undo_stack.push(command)
            super().accept()
            return

        edit = EditTaskCommand.create(self.session, self.task_id, name, duration)
        if isinstance(edit, ValidationError):
            self.show_error(edit)
            return
        changes = predecessor_changes(self.session, self.task_id, preds)
        if isinstance(changes, ValidationError):
            self.show_error(changes)
            return
        to_remove, to_add = changes
        notes_edit = EditNotesCommand.create(self.session, self.task_id, notes)  # can only be None or a command here
        count = (edit is not None) + (notes_edit is not None) + len(to_remove) + len(to_add)
        if count > 1:
            self.undo_stack.beginMacro(self.tr("Edit task “{0}”").format(name.strip()))
        if edit is not None:
            self.undo_stack.push(edit)
        if notes_edit is not None:
            self.undo_stack.push(notes_edit)
        # The whole set was validated above, so each single step is valid when it is created.
        for pred in to_remove:
            self.undo_stack.push(RemoveDependencyCommand.create(self.session, pred, self.task_id))
        for pred in to_add:
            self.undo_stack.push(AddDependencyCommand.create(self.session, pred, self.task_id))
        if count > 1:
            self.undo_stack.endMacro()
        super().accept()
