"""Dialog measuring the distance between two locations (issue #6)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
                               QPushButton, QVBoxLayout)

try:
    from . import routing
except ImportError:
    import routing


class DistanceDialog(QDialog):
    """Straight-line distance between two locations, and on demand their route length and duration."""

    def __init__(self, locations, first=0, parent=None, fetch_route=routing.fetch_route):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Distances"))
        self.setMinimumWidth(420)
        self.locations = list(locations)
        self.fetch_route = fetch_route

        # Created first: filling the boxes below updates them
        self.straight_label = QLabel()
        self.route_label = QLabel()
        self.route_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.from_box, self.to_box = QComboBox(), QComboBox()
        for box in (self.from_box, self.to_box):
            for location in self.locations:
                box.addItem(location.label() or self.tr("(untitled)"))
            box.currentIndexChanged.connect(self.update_straight_distance)
        self.from_box.setCurrentIndex(first)
        self.to_box.setCurrentIndex(first + 1 if first + 1 < len(self.locations) else 0)

        self.mode_box = QComboBox()
        for mode in routing.MODES:
            self.mode_box.addItem(routing.mode_label(mode), mode)
        self.mode_box.currentIndexChanged.connect(lambda: self.route_label.clear())

        self.route_button = QPushButton(self.tr("Compute Route"))
        self.route_button.clicked.connect(self.compute_route)

        attribution = QLabel(routing.attribution_html())
        attribution.setOpenExternalLinks(True)
        attribution.setWordWrap(True)

        form = QFormLayout()
        form.addRow(self.tr("From:"), self.from_box)
        form.addRow(self.tr("To:"), self.to_box)
        form.addRow(self.tr("Straight line:"), self.straight_label)
        form.addRow(self.tr("Mode:"), self.mode_box)
        form.addRow(self.route_button, self.route_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(attribution)
        layout.addWidget(buttons)
        self.update_straight_distance()

    def endpoints(self):
        return self.locations[self.from_box.currentIndex()], self.locations[self.to_box.currentIndex()]

    def update_straight_distance(self):
        start, end = self.endpoints()
        self.straight_label.setText(routing.format_distance(routing.straight_distance(start.location(), end.location())))
        self.route_label.clear()

    def compute_route(self):
        start, end = self.endpoints()
        if start is end:
            self.route_label.setText(self.tr("Choose two different locations."))
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            route = self.fetch_route([start.location(), end.location()], self.mode_box.currentData())
            self.route_label.setText(f"{routing.format_distance(route.distance)}, {routing.format_duration(route.duration)}")
        except routing.RoutingError as e:
            self.route_label.setText(str(e))
        finally:
            QApplication.restoreOverrideCursor()
