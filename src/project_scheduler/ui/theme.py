"""Light and dark themes: application stylesheet plus the table model's colour palette."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QFile, QIODevice, QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

THEMES = ("light", "dark")
DEFAULT_THEME = "light"


@dataclass
class TablePalette:
    critical_background: QColor
    critical_foreground: QColor
    milestone_foreground: QColor


_PALETTES = {
    "light": TablePalette(QColor("#fdecec"), QColor("#9f1d20"), QColor("#5b4bc4")),
    "dark": TablePalette(QColor("#43242a"), QColor("#ffb3b8"), QColor("#b7acff")),
}


class ThemeManager(QObject):
    themeChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.name = DEFAULT_THEME
        self.palette = TablePalette(**vars(_PALETTES[DEFAULT_THEME]))

    def apply(self, name: str) -> None:
        if name not in THEMES:
            name = DEFAULT_THEME
        qss = QFile(f":/styles/{name}.qss")
        if not qss.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            raise RuntimeError(f"theme resource :/styles/{name}.qss missing; run ./build_assets.sh")
        stylesheet = bytes(qss.readAll()).decode("utf-8")
        qss.close()
        self.name = name
        for key, value in vars(_PALETTES[name]).items():
            setattr(self.palette, key, value)
        QApplication.instance().setStyleSheet(stylesheet)
        self.themeChanged.emit(name)


theme_manager = ThemeManager()
