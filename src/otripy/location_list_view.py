import logging

from PySide6.QtWidgets import QListView, QAbstractItemView
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal

try:
    from .journey import Journey
except ImportError:
    from journey import Journey

logger = logging.getLogger(__name__)

class LocationListModel(QAbstractListModel):
    def __init__(self, locations=None, parent=None):
        super().__init__(parent)
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
        # logger.info(f"LocationListModel.setLocations {locations}")
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
            if location.lid == target_id:
                return row
        return -1  # Not found

    def get_location_by_id(self, target_id):
        """Find a location by its UUID."""
        for location in self.locations:
            if location.lid == target_id:
                return location
        return None  # Not found

    def updateLocationNote(self, index, new_note):
        """Update the note of a Location at the given QModelIndex and notify the view."""
        if not index.isValid():
            logger.error("Invalid index.")
            return

        row = index.row()  # Get the row from the QModelIndex
        if 0 <= row < len(self.locations):
            location = self.locations[row]
            location.note = new_note  # Assuming your Location has a 'note' attribute
            # logger.info(f"Updated location {location.lid} note to: {new_note}")

            # Notify the view that data has changed
            self.dataChanged.emit(index, index)  # Emit signal for the changed index

        else:
            logger.error(f"Row {row} is out of range.")

    def delete_item(self, index):
        """Deletes the Location item at the given QModelIndex and updates the view."""
        if not index.isValid():
            logger.error("Invalid index.")
            return

        row = index.row()  # Get the row from the QModelIndex
        if 0 <= row < len(self.locations):
            location = self.locations[row]
            # logger.info(f"Deleting location {location.lid}: {location}")

            # Notify the view that rows are about to be removed
            self.beginRemoveRows(index.parent(), row, row)

            # Remove the location from the list
            del self.locations[row]

            # Notify the view that rows have been removed
            self.endRemoveRows()
        else:
            logger.error(f"Row {row} is out of range.")

    def clear(self):
        """Clears all Location items from the list and updates the view."""
        # logger.info("Clearing all locations.")
        # Notify the view that all rows are being removed
        self.beginResetModel()
        # Clear the list
        self.locations.clear()
        # Notify the view that the model has been reset
        self.endResetModel()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return (Qt.ItemIsEnabled | Qt.ItemIsSelectable
                | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ["application/x-mylistmodel"]

    def mimeData(self, indexes):
        """Serialize data to be dragged"""
        # logger.info(f"LocationListModel.mimeData {indexes}")
        if not indexes:
            return None
        data = indexes[0].row()  # Store row index
        mimeData = super().mimeData(indexes)
        mimeData.setData("application/x-mylistmodel", str(data).encode())
        # logger.info(f"LocationListModel.mimeData: {mimeData}")
        return mimeData

    def dropMimeData(self, data, action, row, column, parent):
        """Handle dropping of data"""
        # logger.info(f"LocationListModel.dropMimeData {data}, {action}, {row}, {column}, {parent}")
        if action != Qt.MoveAction:
            return False
        if not data.hasFormat("application/x-mylistmodel"):
            return False

        old_index = int(data.data("application/x-mylistmodel").data().decode())
        # logger.info(f"LocationListModel.dropMimeData old_index: {old_index}")
        if parent.isValid():
            drop_index = parent
            row = drop_index.row()
            column = drop_index.column()
        else:
            drop_index = self.indexAt(parent)
            if drop_index.isValid():
                row = drop_index.row()
                column = drop_index.column()
            else:
                row = self.model().rowCount()
                column = 0  # Default to column 0

        # logger.info(f"Dropping at row {row}, column {column}")

        self.beginMoveRows(QModelIndex(), old_index, old_index, QModelIndex(), row)
        item = self.locations.pop(old_index)
        # logger.info(f"LocationListModel.dropMimeData dropping: {item} at {row}")
        self.locations.insert(row, item)
        self.endMoveRows()
        return True


class LocationListView(QListView):
    locationClicked = Signal(object)  # Signal emitting the selected Location object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LocationListModel()
        self.setModel(self.model)
        self.clicked.connect(self.on_item_clicked)
        self.setDragDropMode(QListView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dataChanged(self,topLeft, bottomRight, roles=list()):
        self.model.locations.dirty.emit(True)

    def setLocations(self, locations):
        self.model.setLocations(locations)

    def on_item_clicked(self, index):
        """Handles item click and processes the selected location."""
        logger.info(f"LocationListView.on_item_clicked {index}")
        location = self.model.getLocation(index)
        if location:
            logger.info(f"LocationListView.on_item_clicked: {location}")
            self.parent().current_location = location
            self.locationClicked.emit(location)  # Emit signal with clicked location

    def addLocation(self, location):
        self.model.addLocation(location)

    def locations(self):
        return  self.model.get_locations()

    def selectById(self, target_id):
        """Select an item by its UUID."""
        row = self.model.findRowById(target_id)
        # logger.info(f"LocationListView.selectById {target_id}: {row}")
        if row != -1:
            index = self.model.index(row, 0)  # Create QModelIndex
            self.setCurrentIndex(index)  # Select item

    def updateLocationNoteAtIndex(self, index, new_note):
        """Updates the note of the location at a given QModelIndex."""
        self.model.updateLocationNote(index, new_note)

    def deleteItemAtIndex(self, index):
        """Deletes the location at the given QModelIndex."""
        self.model.delete_item(index)

    def clear(self):
        """Clears all locations from the view."""
        self.model.clear()

    def get_location_by_id(self, target_id):
        return  self.model.get_location_by_id(target_id)
