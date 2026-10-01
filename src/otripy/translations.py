"""Load the GUI translations (issue #8).

Otripy's translations are Qt .qm files in the i18n directory, compiled from the
.ts files that translators edit (see the translators' guide in the docs). Qt's
own strings (standard buttons and dialogs) come from Qt's qtbase translations.

The language is the system's, or the one in the OTRIPY_LANGUAGE environment
variable (e.g. OTRIPY_LANGUAGE=fr), which helps translators check their work.
"""
import logging
import os
from importlib import resources

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

logger = logging.getLogger(__name__)


def ui_locale() -> QLocale:
    language = os.environ.get("OTRIPY_LANGUAGE")
    return QLocale(language) if language else QLocale.system()


def install_translators(app, locale: QLocale | None = None) -> list:
    """Install Otripy's and Qt's translators for the locale into app; return them."""
    locale = locale or ui_locale()
    installed = []
    qt_translator = QTranslator(app)
    if qt_translator.load(locale, "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(qt_translator)
        installed.append(qt_translator)
    otripy_translator = QTranslator(app)
    # The translator reads the file at load: a temporary extraction (zipped package) is fine
    with resources.as_file(resources.files("otripy") / "i18n") as directory:
        if otripy_translator.load(locale, "otripy", "_", str(directory)):
            app.installTranslator(otripy_translator)
            installed.append(otripy_translator)
    logger.info(f"Translations for {locale.uiLanguages()}: {[t.filePath() for t in installed]}")
    return installed
