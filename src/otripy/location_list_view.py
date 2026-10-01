import logging
from functools import lru_cache
from importlib import resources

from PySide6.QtWidgets import QListView, QAbstractItemView
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

try:
    from .journey import Journey
    from .limited_color_picker import LimitedColorPicker
except ImportError:
    from journey import Journey
    from limited_color_picker import LimitedColorPicker

logger = logging.getLogger(__name__)

ICON_SIZE = 32  # drawn size, scaled down for display
LIST_ICON_SIZE = 16
DEFAULT_MARKER_COLOR = "blue"


@lru_cache(maxsize=1)
def blank_icon() -> QIcon:
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.transparent)
    return QIcon(pixmap)


@lru_cache(maxsize=None)
def marker_icon(marker: str, color: str | None) -> QIcon:
    """Return the Font Awesome icon of a marker, drawn in the marker's color.

    Returns a null QIcon if the icon is unknown.
    """
    svg = resources.files("otripy.resources.icons") / f"{marker}.svg"
    if not svg.is_file():
        return QIcon()
    with resources.as_file(svg) as path:
        pixmap = QIcon(str(path)).pixmap(ICON_SIZE, ICON_SIZE)
    rgb = LimitedColorPicker.COLORS.get(color or DEFAULT_MARKER_COLOR, LimitedColorPicker.COLORS[DEFAULT_MARKER_COLOR])
    # Keep the glyph's shape, paint it in the marker color
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(*rgb))
    painter.end()
    return QIcon(pixmap)

class LocationListModel(QAbstractListModel):
    """Qt list model over a Journey: one row per Location, displayed by its label.

    Rows can be reordered by drag and drop (internal moves only).
    """

    def __init__(self, locations=None, parent=None):
        super().__init__(parent)
        # An empty Journey is falsy: test for None, not truth
        self.locations = locations if locations is not None else Journey()

    def rowCount(self, parent=None):
        return len(self.locations)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.locations):
            return None
        location = self.locations[index.row()]
        if role == Qt.DisplayRole:
            return str(location)
        if role == Qt.DecorationRole:
            # Only custom markers show an icon (issue #27); others get a blank
            # one so that all titles are aligned and rows have the same height
            icon = marker_icon(location.marker, location.color) if location.marker else QIcon()
            return icon if not icon.isNull() else blank_icon()
        return None

    def setMarkerStyle(self, index: QModelIndex, marker=..., color=...):
        """Change a location's marker icon and/or color, and notify the views."""
        location = self.getLocation(index)
        if location is None:
            return
        if marker is not ...:
            location.marker = marker
        if color is not ...:
            location.color = color
        self.dataChanged.emit(index, index)

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
        # Qt gives the insertion row for drops between items, or the target
        # item as parent for drops onto an item, which takes its place.
        if row != -1:
            destination = row
        elif parent.isValid():
            destination = parent.row() + 1 if parent.row() > old_index else parent.row()
        else:
            destination = self.rowCount()

        # beginMoveRows refuses moves that leave the item in place
        if not self.beginMoveRows(QModelIndex(), old_index, old_index, QModelIndex(), destination):
            return False
        item = self.locations.pop(old_index)
        self.locations.insert(destination - 1 if destination > old_index else destination, item)
        self.endMoveRows()
        return True


class LocationListView(QListView):
    """The list of locations next to the map. Emits locationClicked(Location)."""

    locationClicked = Signal(object)  # Signal emitting the selected Location object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LocationListModel()
        self.setModel(self.model)
        self.clicked.connect(self.on_item_clicked)
        self.setDragDropMode(QListView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIconSize(QSize(LIST_ICON_SIZE, LIST_ICON_SIZE))

    def dataChanged(self, topLeft, bottomRight, roles=()):
        super().dataChanged(topLeft, bottomRight, roles)
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
