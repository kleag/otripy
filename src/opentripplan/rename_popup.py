from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

class RenamePopup(QDialog):
    def __init__(self, parent: QWidget = None, old_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Choose a New Name")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        self.label = QLabel("File has changed. Enter a new name:")
        layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.line_edit.setText(old_name)
        layout.addWidget(self.line_edit)

        self.try_button = QPushButton("Try a new name")
        self.try_button.setEnabled(False)  # Disabled until input is given
        layout.addWidget(self.try_button)

        self.cancel_button = QPushButton("Cancel")
        layout.addWidget(self.cancel_button)

        self.line_edit.textChanged.connect(self.toggle_try_button)
        self.cancel_button.clicked.connect(self.reject)
        self.try_button.clicked.connect(self.accept)

    def toggle_try_button(self, text):
        self.try_button.setEnabled(bool(text.strip()))

if __name__ == "__main__":
    app = QApplication([])

    dialog = RenamePopup()
    if dialog.exec():
        print("New name:", dialog.line_edit.text())
    else:
        print("Canceled")

    app.quit()
