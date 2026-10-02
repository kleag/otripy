"""Dialog choosing how to export a trip for a phone (issue #47)."""
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton, QRadioButton,
                               QVBoxLayout)

KMZ, GPX = "kmz", "gpx"
FILE, NEXTCLOUD = "file", "nextcloud"


class ExportDialog(QDialog):
    """Choose the format (KMZ for Organic Maps, GPX for other apps), the route, and where to save."""

    def __init__(self, parent=None, has_route=False, route_label=""):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Export for Phone"))
        self.setMinimumWidth(420)
        self.destination = None

        intro = QLabel(self.tr("Export the trip to use it in a map app on your phone, even offline. "
                               "Notes are included, without their images."))
        intro.setWordWrap(True)
        self.kmz_button = QRadioButton(self.tr("KMZ, for Organic Maps (each group becomes a list)"))
        self.gpx_button = QRadioButton(self.tr("GPX, for OsmAnd and other apps"))
        self.kmz_button.setChecked(True)
        self.formats = QButtonGroup(self)
        self.formats.addButton(self.kmz_button)
        self.formats.addButton(self.gpx_button)

        self.route_box = QCheckBox(self.tr("Include the route shown on the map ({route})").format(route=route_label)
                                   if has_route else self.tr("Include the route (show a route on the map first)"))
        self.route_box.setChecked(has_route)
        self.route_box.setEnabled(has_route)

        self.file_button = QPushButton(self.tr("Save to File…"))
        self.nextcloud_button = QPushButton(self.tr("Save to Nextcloud…"))
        self.file_button.clicked.connect(lambda: self.choose(FILE))
        self.nextcloud_button.clicked.connect(lambda: self.choose(NEXTCLOUD))
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.addButton(self.file_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.nextcloud_button, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.kmz_button)
        layout.addWidget(self.gpx_button)
        layout.addWidget(self.route_box)
        layout.addWidget(buttons)

    def choose(self, destination):
        self.destination = destination
        self.accept()

    def export_format(self) -> str:
        return KMZ if self.kmz_button.isChecked() else GPX

    def include_route(self) -> bool:
        return self.route_box.isEnabled() and self.route_box.isChecked()
