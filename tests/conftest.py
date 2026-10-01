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
def isolated_settings(tmp_path):
    """Keep tests away from the user's real Otripy settings (QSettings("Kleag", "Otripy")).

    On Linux, settings are files and go to a temporary directory. On Windows
    and macOS native settings (registry, preferences) ignore QSettings.setPath:
    there tests use the real ones, which is harmless on CI runners.
    """
    from PySide6.QtCore import QSettings

    for scope in (QSettings.UserScope, QSettings.SystemScope):
        QSettings.setPath(QSettings.NativeFormat, scope, str(tmp_path / "settings"))
        QSettings.setPath(QSettings.IniFormat, scope, str(tmp_path / "settings"))
    # Do not let keyring touch the user's real keyring either
    import keyring
    from keyring.backends.fail import Keyring as FailKeyring
    keyring.set_keyring(FailKeyring())
    yield tmp_path / "settings"
