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
