from datetime import date

import pytest
from PySide6.QtCore import QSettings

import project_scheduler.resources_rc  # noqa: F401  (build with ./build_assets.sh --no-run)
from project_scheduler.domain import Project, Task, WorkCalendar
from project_scheduler.ui.i18n import language_manager
from project_scheduler.ui.main_window import MainWindow
from project_scheduler.ui.session import ProjectSession
from project_scheduler.ui.settings import AppSettings
from project_scheduler.ui.theme import theme_manager


def small_project() -> Project:
    """A (3d) -> B (2d) -> D (1d), C (1d) -> D; start Fri 2026-01-02."""
    return Project(
        WorkCalendar(date(2026, 1, 2)),
        [
            Task(1, "Design", 3),
            Task(2, "Build", 2, [1]),
            Task(3, "Docs", 1),
            Task(4, "Launch", 1, [2, 3]),
        ],
        next_id=5,
    )


@pytest.fixture(autouse=True)
def pinned_locale_and_theme(qapp):
    """Tests never depend on the host locale or on a previous test's language/theme."""
    language_manager.set_language("en")
    theme_manager.apply("light")
    yield
    language_manager.set_language("en")
    theme_manager.apply("light")


@pytest.fixture
def settings(tmp_path):
    return AppSettings(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


@pytest.fixture
def session(qapp):
    return ProjectSession(small_project())


@pytest.fixture
def window(qtbot, settings):
    w = MainWindow(settings, small_project())
    # pytest-qt closes widgets before fixture teardown; mark clean first so closing never prompts.
    qtbot.addWidget(w, before_close_func=lambda win: win.undo_stack.setClean())
    w.show()
    qtbot.waitExposed(w)
    return w


@pytest.fixture
def answer_modal(qtbot):
    """Answer the next blocking modal dialog (QMessageBox.question, QFileDialog.get*FileName).

    Those calls don't return until the dialog is closed, so the answer is queued first and runs
    inside the dialog's own event loop once the dialog is the active modal widget. The returned
    list records each dialog that was answered, so tests can inspect it.
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    answered = []

    def schedule(action, attempts=500):
        def poll(remaining=attempts):
            dialog = QApplication.activeModalWidget()
            if dialog is None:
                if remaining:
                    QTimer.singleShot(10, lambda: poll(remaining - 1))
                return
            answered.append(dialog)
            action(dialog)

        QTimer.singleShot(0, poll)
        return answered

    yield schedule
    assert QApplication.activeModalWidget() is None, "a modal dialog was left open"
