"""Runtime language switching."""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QLocale, QObject, QTranslator, Signal
from PySide6.QtWidgets import QApplication

# Language code -> locale. The menu names are translated in MainWindow.retranslate_ui().
LANGUAGES = {
    "en": "en_US",
    "de": "de_DE",
    "ja": "ja_JP",
}
# Each language in its own name, shown next to the translated name so it can be found even
# after switching to a language you can't read. Deliberately not translated.
NATIVE_NAMES = {
    "en": "English",
    "de": "Deutsch",
    "ja": "日本語",
}
DEFAULT_LANGUAGE = "en"


class LanguageManager(QObject):
    """Swaps translators and the default QLocale; emits languageChanged afterwards."""

    languageChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.code = DEFAULT_LANGUAGE
        self._translators: list[QTranslator] = []

    def set_language(self, code: str) -> None:
        if code not in LANGUAGES:
            code = DEFAULT_LANGUAGE
        app = QApplication.instance()
        for translator in self._translators:
            app.removeTranslator(translator)
        self._translators = []

        # Set the locale first so LanguageChange handlers already format with it.
        QLocale.setDefault(QLocale(LANGUAGES[code]))
        self.code = code
        if code != "en":
            qt_translator = QTranslator()
            if qt_translator.load(f"qtbase_{code}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                self._translators.append(qt_translator)
            app_translator = QTranslator()
            if not app_translator.load(f":/i18n/project_scheduler_{code}.qm"):
                raise RuntimeError(f"translation :/i18n/project_scheduler_{code}.qm missing; run ./build_assets.sh")
            self._translators.append(app_translator)
        for translator in self._translators:
            app.installTranslator(translator)
        self.languageChanged.emit(code)


language_manager = LanguageManager()
