"""Every command: redo -> undo -> redo returns to identical state; rejected edits push nothing."""

import copy
from datetime import date

import pytest
from PySide6.QtGui import QUndoStack

from project_scheduler.domain import ValidationError, compute_schedule
from project_scheduler.domain.validation import ErrorCode
from project_scheduler.samples import generate_sample
from project_scheduler.ui.commands import (
    AddDependencyCommand,
    AddTaskCommand,
    ChangeStartDateCommand,
    DeleteTasksCommand,
    EditCalendarCommand,
    EditTaskCommand,
    RemoveDependencyCommand,
)
from project_scheduler.ui.session import ProjectSession
from project_scheduler.ui.task_model import TaskTableModel

COMMANDS = {
    "add_task": lambda s: AddTaskCommand.create(s, "  QA  ", 4, [2, 3]),
    "edit_task": lambda s: EditTaskCommand.create(s, 2, name="Build v2", duration=7),
    "delete_one": lambda s: DeleteTasksCommand.create(s, [2]),
    "delete_many": lambda s: DeleteTasksCommand.create(s, [1, 3]),
    "add_dependency": lambda s: AddDependencyCommand.create(s, 3, 2),
    "remove_dependency": lambda s: RemoveDependencyCommand.create(s, 2, 4),
    "edit_calendar": lambda s: EditCalendarCommand.create(s, {0, 1, 2}, {date(2026, 1, 7)}),
    "change_start_date": lambda s: ChangeStartDateCommand.create(s, date(2026, 2, 1)),
}


def state(session: ProjectSession):
    return copy.deepcopy(session.project), session.schedule


@pytest.mark.parametrize("name", COMMANDS)
def test_redo_undo_redo_is_identical(session, name):
    model = TaskTableModel(session)
    stack = QUndoStack()
    before = state(session)
    command = COMMANDS[name](session)
    assert command is not None and not isinstance(command, ValidationError)

    stack.push(command)
    after = state(session)
    assert after[0] != before[0]
    assert session.schedule == compute_schedule(session.project)
    assert model.rowCount() == len(session.project.tasks)

    stack.undo()
    assert state(session) == before
    assert model.rowCount() == len(before[0].tasks)
    stack.redo()
    assert state(session) == after
    stack.undo()
    assert state(session) == before


def test_add_task_strips_name_and_assigns_next_id(session):
    AddTaskCommand.create(session, "  QA  ", 1).redo()
    task = session.project.tasks[-1]
    assert (task.id, task.name) == (5, "QA")
    assert session.project.next_id == 6


def test_delete_removes_dependencies_and_undo_restores_order(session):
    stack = QUndoStack()
    stack.push(DeleteTasksCommand.create(session, [2]))
    assert session.project.find(4).predecessors == [3]
    stack.undo()
    assert [t.id for t in session.project.tasks] == [1, 2, 3, 4]
    assert session.project.find(4).predecessors == [2, 3]


def test_bulk_delete_of_200_rows_is_one_undo_step(qapp):
    session = ProjectSession(generate_sample(1000))
    model = TaskTableModel(session)
    before = copy.deepcopy(session.project)
    stack = QUndoStack()
    ids = [t.id for t in session.project.tasks[::5]]
    stack.push(DeleteTasksCommand.create(session, ids))
    assert stack.count() == 1
    assert model.rowCount() == 800
    stack.undo()
    assert session.project == before
    assert model.rowCount() == 1000


@pytest.mark.parametrize("make, code", [
    (lambda s: AddTaskCommand.create(s, "  ", 1), ErrorCode.EMPTY_NAME),
    (lambda s: AddTaskCommand.create(s, "X", 10_000), ErrorCode.DURATION_RANGE),
    (lambda s: AddTaskCommand.create(s, "X", 1, [42]), ErrorCode.UNKNOWN_PREDECESSOR),
    (lambda s: EditTaskCommand.create(s, 1, name=""), ErrorCode.EMPTY_NAME),
    (lambda s: EditTaskCommand.create(s, 1, duration=-1), ErrorCode.DURATION_RANGE),
    (lambda s: AddDependencyCommand.create(s, 1, 1), ErrorCode.SELF_DEPENDENCY),
    (lambda s: AddDependencyCommand.create(s, 4, 1), ErrorCode.CYCLE),
    (lambda s: AddDependencyCommand.create(s, 1, 2), ErrorCode.DUPLICATE_DEPENDENCY),
    (lambda s: EditCalendarCommand.create(s, set(), set()), ErrorCode.NO_WORKING_DAYS),
    (lambda s: DeleteTasksCommand.create(s, [99]), ErrorCode.UNKNOWN_TASK),
])
def test_rejected_edit_pushes_nothing(session, make, code):
    stack = QUndoStack()
    before = copy.deepcopy(session.project)
    result = make(session)
    assert isinstance(result, ValidationError)
    assert result.code is code
    assert stack.count() == 0
    assert session.project == before


def test_cycle_error_carries_path(session):
    err = AddDependencyCommand.create(session, 4, 1)
    assert err.data["path"] == (1, 2, 4, 1)


def test_no_op_edits_return_none(session):
    assert EditTaskCommand.create(session, 1, name="Design", duration=3) is None
    assert ChangeStartDateCommand.create(session, date(2026, 1, 2)) is None
    assert EditCalendarCommand.create(session, {0, 1, 2, 3, 4}, set()) is None
    assert DeleteTasksCommand.create(session, []) is None
