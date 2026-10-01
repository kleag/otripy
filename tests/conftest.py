import os
from pathlib import Path

import pytest

# Run Qt without a display; must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    """Return the content of a file in tests/fixtures."""
    return lambda name: (FIXTURES / name).read_text(encoding="utf-8")
