import os
import sys
from pathlib import Path

import pytest

# Run Qt without a display; must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if sys.platform == "win32":
    # On Windows the offscreen platform only looks for fonts in Qt's own fonts
    # directory, which PySide6 does not ship. Without a font that has a bold
    # face, QTextDocument.toMarkdown drops bold markup.
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    """Return the content of a file in tests/fixtures."""
    return lambda name: (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Give each test fresh settings and keyring, never the user's real ones.

    Settings go to a temporary INI file on every platform: on Windows and macOS
    native settings (registry, preferences) would ignore QSettings.setPath and
    leak from one test to the next.
    """
    from PySide6.QtCore import QSettings

    from otripy import settings

    path = str(tmp_path / "otripy.ini")
    monkeypatch.setattr(settings, "app_settings", lambda: QSettings(path, QSettings.IniFormat))
    import keyring
    from keyring.backends.fail import Keyring as FailKeyring
    keyring.set_keyring(FailKeyring())
    yield path
