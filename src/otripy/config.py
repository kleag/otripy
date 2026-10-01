import logging

import keyring
from keyring.errors import KeyringError
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "Otripy"
KEYRING_USERNAME = "nextcloud"
PASSWORD_SETTING = "nextcloud/password"


def load_nextcloud_password(settings) -> str:
    """Return the Nextcloud password from the system keyring.

    A password left in plaintext settings by older versions is moved to the
    keyring. If no keyring backend is usable, fall back to the settings.
    """
    legacy_password = settings.value(PASSWORD_SETTING, "")
    try:
        password = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if password is None and legacy_password:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, legacy_password)
            settings.remove(PASSWORD_SETTING)
            password = legacy_password
        return password or ""
    except KeyringError as e:
        logger.warning(f"System keyring unavailable, using plaintext settings: {e}")
        return legacy_password


def save_nextcloud_password(settings, password: str):
    """Store the Nextcloud password in the system keyring, or in the settings if no keyring is usable."""
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)
        settings.remove(PASSWORD_SETTING)
    except KeyringError as e:
        logger.warning(f"System keyring unavailable, storing password in plaintext settings: {e}")
        settings.setValue(PASSWORD_SETTING, password)


class ConfigDialog(QDialog):
    """Dialog for configuring Nextcloud settings"""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Configure Otripy"))

        # Create widgets
        self.url_label = QLabel(self.tr("Nextcloud URL:"))
        self.url_input = QLineEdit()

        self.username_label = QLabel(self.tr("Nextcloud Username:"))
        self.username_input = QLineEdit()

        self.password_label = QLabel(self.tr("Nextcloud Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)  # Hide password

        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.clicked.connect(self.save_settings)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        # Load existing settings
        self.load_settings()

    def load_settings(self):
        """Load settings from QSettings"""
        self.url_input.setText(self.settings.value("nextcloud/url", ""))
        self.username_input.setText(self.settings.value("nextcloud/username", ""))
        self.password_input.setText(load_nextcloud_password(self.settings))

    def save_settings(self):
        """Save settings to QSettings"""
        self.settings.setValue("nextcloud/url", self.url_input.text())
        self.settings.setValue("nextcloud/username", self.username_input.text())
        save_nextcloud_password(self.settings, self.password_input.text())
        self.accept()  # Close the dialog
