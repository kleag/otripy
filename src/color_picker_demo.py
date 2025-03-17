from PySide6.QtWidgets import QApplication, QColorDialog, QPushButton, QWidget, QVBoxLayout
from PySide6.QtGui import QColor

class ColorPickerDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Color Picker Example")

        self.button = QPushButton("Pick a Color")
        self.button.clicked.connect(self.open_color_picker)

        layout = QVBoxLayout()
        layout.addWidget(self.button)
        self.setLayout(layout)

    def open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():  # User picked a color
            self.button.setStyleSheet(f"background-color: {color.name()};")

if __name__ == "__main__":
    app = QApplication([])
    window = ColorPickerDemo()
    window.show()
    app.exec()
