"""Persistent user preferences (QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from .i18n import DEFAULT_LANGUAGE, LANGUAGES
from .theme import DEFAULT_THEME, THEMES

MAX_RECENT = 8


class AppSettings:
    def __init__(self, qsettings: QSettings | None = None) -> None:
        self._s = qsettings or QSettings()

    def _str(self, key: str, default: str) -> str:
        value = self._s.value(key, default)
        return value if isinstance(value, str) else default

    @property
    def theme(self) -> str:
        value = self._str("view/theme", DEFAULT_THEME)
        return value if value in THEMES else DEFAULT_THEME

    @theme.setter
    def theme(self, value: str) -> None:
        self._s.setValue("view/theme", value)

    @property
    def language(self) -> str:
        value = self._str("view/language", DEFAULT_LANGUAGE)
        return value if value in LANGUAGES else DEFAULT_LANGUAGE

    @language.setter
    def language(self, value: str) -> None:
        self._s.setValue("view/language", value)

    @property
    def recent_files(self) -> list[str]:
        value = self._s.value("files/recent", [])
        if isinstance(value, str):  # QSettings returns a bare string for one-item lists
            value = [value]
        return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []

    def add_recent_file(self, path: str) -> None:
        files = [path] + [f for f in self.recent_files if f != path]
        self._s.setValue("files/recent", files[:MAX_RECENT])

    def remove_recent_file(self, path: str) -> None:
        self._s.setValue("files/recent", [f for f in self.recent_files if f != path])

    @property
    def last_file(self) -> str:
        return self._str("files/last", "")

    @last_file.setter
    def last_file(self, value: str) -> None:
        self._s.setValue("files/last", value)

    def sync(self) -> None:
        self._s.sync()
