"""Access to Otripy's settings, in one place so that tests can replace them."""
from PySide6.QtCore import QSettings

ORGANIZATION = "Kleag"
APPLICATION = "Otripy"


def app_settings() -> QSettings:
    """Return Otripy's settings (the platform's native storage: files, registry or preferences)."""
    return QSettings(ORGANIZATION, APPLICATION)
