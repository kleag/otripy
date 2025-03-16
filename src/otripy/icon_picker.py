import os
import sys
import time
from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QVBoxLayout, QDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

# Directory where the icons are stored
RESOURCE_DIR = "resources/icons"
# List of Folium marker icon names
ICON_NAMES = [
    "location-dot", "cloud", "info-sign", "home", "star", "flag", "ok",
    "remove", "plus", "minus", "heart"
]

class IconPickerWidget(QDialog):
    icon_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick an Icon")
        self.setFixedSize(400, 300)

        self.layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.load_icons()

    def load_icons(self):
        icon_files = [f for f in os.listdir(RESOURCE_DIR) if f.endswith(".svg")]
        print(icon_files)
        for idx, icon_name in enumerate(ICON_NAMES):
            icon_file = f"{icon_name}.svg"
            if icon_file in icon_files:
                print(f"load icon {idx}, {icon_file}", file=sys.stderr)
                icon_path = os.path.join(RESOURCE_DIR, icon_file)
                icon_button = QPushButton()
                icon_button.setIcon(QIcon(icon_path))
                icon_button.setIconSize(self.sizeHint())

                row, col = divmod(idx, 5)  # Arrange in a grid
                self.grid_layout.addWidget(icon_button, row, col)

                icon_button.clicked.connect(lambda _, name=icon_name: self.select_icon(name))

    def select_icon(self, icon_name):
        self.icon_selected.emit(icon_name)
        self.accept()

# Example usage:
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QPushButton, QMainWindow

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Folium Icon Picker Example")
            self.setGeometry(100, 100, 300, 200)

            self.button = QPushButton("Choose Icon", self)
            self.button.clicked.connect(self.open_icon_picker)
            self.setCentralWidget(self.button)

        def open_icon_picker(self):
            self.dialog = IconPickerWidget(self)
            self.dialog.icon_selected.connect(self.icon_chosen)
            self.dialog.exec()

        def icon_chosen(self, icon_name):
            print(f"Selected icon: {icon_name}")

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
