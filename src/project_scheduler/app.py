"""Application start-up."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .ui.i18n import LANGUAGES
from .ui.theme import THEMES


def _import_resources() -> None:
    try:
        from . import resources_rc  # noqa: F401  (registers :/styles, :/icons, :/i18n)
    except ModuleNotFoundError:
        sys.exit("Qt resources are not built. Run: ./build_assets.sh")


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Our options; anything else (e.g. Qt's own -style) is passed on to QApplication."""
    parser = argparse.ArgumentParser(
        prog="project-scheduler", description="Critical-path project scheduler."
    )
    parser.add_argument(
        "--language", choices=sorted(LANGUAGES),
        help="interface language for this run (default: the one chosen in View > Language)",
    )
    parser.add_argument(
        "--theme", choices=THEMES,
        help="colour theme for this run (default: the one chosen in View > Theme)",
    )
    return parser.parse_known_args(argv[1:])


def main() -> int:
    args, qt_args = parse_args(sys.argv)
    app = QApplication([sys.argv[0], *qt_args])
    app.setOrganizationName("project-scheduler")
    app.setApplicationName("project-scheduler")
    _import_resources()

    from .ui.i18n import language_manager
    from .ui.main_window import MainWindow
    from .ui.settings import AppSettings
    from .ui.theme import theme_manager

    settings = AppSettings()
    # Command-line choices apply to this run only; the View menu changes the saved preference.
    language_manager.set_language(args.language or settings.language)
    theme_manager.apply(args.theme or settings.theme)
    window = MainWindow(settings)
    window.show()
    if settings.last_file:
        window.open_path(Path(settings.last_file), quiet_if_missing=True)
    return app.exec()
