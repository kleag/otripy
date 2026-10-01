from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMenuBar
from PySide6.QtCore import QSettings


class ConfigDialog(QDialog):
    """Dialog for configuring Nextcloud settings"""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Configure Otripy")

        # Create widgets
        self.url_label = QLabel("Nextcloud URL:")
        self.url_input = QLineEdit()

        self.username_label = QLabel("Nextcloud Username:")
        self.username_input = QLineEdit()

        self.password_label = QLabel("Nextcloud Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)  # Hide password

        self.save_button = QPushButton("Save")
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
        self.password_input.setText(self.settings.value("nextcloud/password", ""))

    def save_settings(self):
        """Save settings to QSettings"""
        self.settings.setValue("nextcloud/url", self.url_input.text())
        self.settings.setValue("nextcloud/username", self.username_input.text())
        self.settings.setValue("nextcloud/password", self.password_input.text())
        self.accept()  # Close the dialog
