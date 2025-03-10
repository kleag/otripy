import logging

from PySide6.QtWidgets import QListView
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal

try:
    from .journey import Journey
except ImportError:
    from journey import Journey

logger = logging.getLogger(__name__)

class LocationListModel(QAbstractListModel):
    def __init__(self, locations=None):
        super().__init__()
        self.locations = locations or Journey()

    def rowCount(self, parent=None):
        return len(self.locations)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.locations):
            return None
        if role == Qt.DisplayRole:
            return str(self.locations[index.row()])
        return None

    def setLocations(self, locations):
        logger.info(f"LocationListModel.setLocations {locations}")
        self.beginResetModel()
        self.locations = locations
        self.endResetModel()

    def getLocation(self, index: QModelIndex):
        """Returns the Location object for a given index."""
        if index.isValid() and 0 <= index.row() < len(self.locations):
            return self.locations[index.row()]
        return None

    def addLocation(self, location):
        """Adds a location to the list and updates the view."""
        logger.info(f"LocationListModel.addLocation {location}")
        self.beginInsertRows(self.index(len(self.locations), 0), len(self.locations), len(self.locations))
        self.locations.append(location)
        self.endInsertRows()

    def get_locations(self):
        return self.locations

    def findRowById(self, target_id):
        """Find the row index of a location by its UUID."""
        for row, location in enumerate(self.locations):
            if location.id == target_id:
                return row
        return -1  # Not found

class LocationListView(QListView):
    locationClicked = Signal(object)  # Signal emitting the selected Location object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LocationListModel()
        self.setModel(self.model)
        self.clicked.connect(self.on_item_clicked)  # Connect view click to slot

    def setLocations(self, locations):
        self.model.setLocations(locations)

    def on_item_clicked(self, index):
        """Handles item click and processes the selected location."""
        location = self.model.getLocation(index)
        if location:
            logger.info(f"LocationListView.on_item_clicked: {location}")
            self.locationClicked.emit(location)  # Emit signal with clicked location

    def addLocation(self, location):
        self.model.addLocation(location)

    def locations(self):
        return  self.model.get_locations()

    def selectById(self, target_id):
        """Select an item by its UUID."""
        row = self.model.findRowById(target_id)
        logger.info(f"LocationListView.selectById {target_id}: {row}")
        if row != -1:
            index = self.model.index(row, 0)  # Create QModelIndex
            self.setCurrentIndex(index)  # Select item
