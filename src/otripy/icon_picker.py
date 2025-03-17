from importlib import resources
import logging
import os
import sys
import time
from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QVBoxLayout, QDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Signal

logger = logging.getLogger(__name__)

# Directory where the icons are stored
RESOURCE_DIR = "resources/icons"
# List of Folium marker icon names
ICON_NAMES = [
    "address-book",
    "address-card",
    "anchor",
    "arrows-to-circle",
    "bag-shopping",
    "bed",
    "bicycle",
    "binoculars",
    "briefcase",
    "bus",
    "cable-car",
    "camera",
    "campground",
    "cannabis",
    "car-side",
    "caravan",
    "charging-station",
    "city",
    "cloud",
    "compass",
    "ferry",
    "flag",
    "globe",
    "guitar",
    "heart",
    "helicopter",
    "home",
    "hotel",
    "info-sign",
    "landmark",
    "location-arrow",
    "location-crosshairs",
    "location-dot",
    "location-pin-lock",
    "location-pin",
    "map-location-dot",
    "map-location",
    "map-pin",
    "map",
    "marker",
    "motorcycle",
    "mountain",
    "passport",
    "person-biking",
    "person-hiking",
    "person-running",
    "person-skating",
    "person-skiing-nordic",
    "person-skiing",
    "person-snowboarding",
    "person-swimming",
    "person-walking-luggage",
    "plane-departure",
    "route",
    "sailboat",
    "ship",
    "star",
    "suitcase-medical",
    "suitcase-rolling",
    "suitcase",
    "taxi",
    "train-subway",
    "train",
    "umbrella-beach",
    "utensils",
    "wine-glass",
]

class IconPickerWidget(QDialog):
    icon_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick an Icon")
        self.setFixedSize(300, 300)

        self.layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.load_icons()

    def load_icons(self):
        # logger.info(f"resources.files: {resources.files("otripy.resources.icons")}")

        if resources.files("otripy.resources.icons"):  # Check if the module is available
            # Use importlib.resources to list all SVG files in the package resources
            icon_dir = resources.files("otripy.resources.icons")
            svg_files = {f.name: f"{icon_dir}/{f.name}" for f in icon_dir.iterdir() if f.suffix == ".svg"}
        else:
            # Fallback to local directory if not installed
            svg_files = {f: f"{RESOURCE_DIR}/{f}" for f in os.listdir(RESOURCE_DIR) if f.endswith(".svg")}

        for idx, icon_name in enumerate(ICON_NAMES):
            icon_file = f"{icon_name}.svg"
            if icon_file in svg_files:
                # logger.info(f"load icon {idx}, {svg_files[icon_file]}")
                icon_button = QPushButton()
                icon = QIcon(svg_files[icon_file])
                # logger.info(f"icon {icon.size()}")
                icon_button.setIcon(icon)
                # icon_button.setIconSize(self.sizeHint())
                icon_button.setIconSize(QSize(20, 20))

                row, col = divmod(idx, 8)  # Arrange in a grid
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
