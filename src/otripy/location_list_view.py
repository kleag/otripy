import logging
from functools import lru_cache
from importlib import resources

from PySide6.QtWidgets import QAbstractItemView, QApplication, QListView, QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QSize, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPalette, QPixmap

try:
    from .journey import Journey
    from .limited_color_picker import LimitedColorPicker
    from .location import Group, Location, TripNotes
except ImportError:
    from journey import Journey
    from limited_color_picker import LimitedColorPicker
    from location import Group, Location, TripNotes

logger = logging.getLogger(__name__)

ICON_SIZE = 32  # drawn size, scaled down for display
LIST_ICON_SIZE = 16
DEFAULT_MARKER_COLOR = "blue"
GROUP_INDENT = 16  # pixels, for the locations of a group
INDENT_ROLE = Qt.UserRole + 1  # True for locations shown inside a group
MIME_TYPE = "application/x-mylistmodel"


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
    """Qt list model over a Journey.

    Its rows are, in order: the trip's notes (issue #19), the ungrouped
    locations, then each group's title followed by its locations (issue #18);
    collapsed groups show no location rows. Rows are entries: TripNotes, Group
    or Location objects. They can be reordered by drag and drop (internal
    moves only): a location joins the section it is dropped in, a group moves
    with its locations.
    """
    arranged = Signal()  # entries were reordered, grouped or collapsed

    def __init__(self, locations=None, parent=None):
        super().__init__(parent)
        # An empty Journey is falsy: test for None, not truth
        self.locations = locations if locations is not None else Journey()
        self.hovered_id = None  # location whose marker the mouse is over, on the map
        self._rows = []
        self._build_rows()

    def _build_rows(self):
        journey = self.locations
        self._rows = [journey.notes, *journey.group_locations(None)]
        for group in journey.groups:
            self._rows.append(group)
            if not group.collapsed:
                self._rows.extend(journey.group_locations(group))

    def _rebuild(self):
        """Rebuild all the rows after a structural change."""
        self.beginResetModel()
        self._build_rows()
        self.endResetModel()

    # Reading
    def rowCount(self, parent=None):
        return len(self._rows)

    def entry(self, row: int):
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def getEntry(self, index: QModelIndex):
        """Return the TripNotes, Group or Location of a row, or None."""
        return self.entry(index.row()) if index.isValid() else None

    def getLocation(self, index: QModelIndex):
        """Return the Location of a row, or None for other rows."""
        entry = self.getEntry(index)
        return entry if isinstance(entry, Location) else None

    def rowOf(self, entry) -> int:
        return next((row for row, e in enumerate(self._rows) if e is entry), -1)

    def data(self, index, role):
        entry = self.getEntry(index)
        if entry is None:
            return None
        if isinstance(entry, TripNotes):
            return self._trip_notes_data(entry, role)
        if isinstance(entry, Group):
            return self._group_data(entry, role)
        return self._location_data(entry, role)

    def _trip_notes_data(self, notes, role):
        if role == Qt.DisplayRole:
            return self.tr("Trip notes")
        if role == Qt.DecorationRole:
            return marker_icon("book", "gray")
        if role == Qt.FontRole:
            return bold_font()
        if role == Qt.ToolTipRole:
            return notes.preview() or self.tr("General notes about the trip")
        return None

    def _group_data(self, group, role):
        if role == Qt.DisplayRole:
            arrow = "▸" if group.collapsed else "▾"
            title = group.label() or self.tr("(untitled group)")
            return f"{arrow} {title} ({len(self.locations.group_locations(group))})"
        if role == Qt.DecorationRole:
            return marker_icon("folder" if group.collapsed else "folder-open", "cadetblue")
        if role == Qt.FontRole:
            return bold_font()
        if role == Qt.ToolTipRole:
            hint = self.tr("Double-click to collapse or expand")
            return "\n".join(part for part in (group.label(), group.preview(), hint) if part)
        return None

    def _location_data(self, location, role):
        if role == Qt.DisplayRole:
            return str(location)
        if role == Qt.DecorationRole:
            # Only custom markers show an icon (issue #27); others get a blank
            # one so that all titles are aligned and rows have the same height
            icon = marker_icon(location.marker, location.color) if location.marker else QIcon()
            return icon if not icon.isNull() else blank_icon()
        if role == Qt.ToolTipRole:
            return "\n".join(part for part in (location.label(), location.preview()) if part)
        if role == Qt.BackgroundRole and location.lid == self.hovered_id:
            highlight = QApplication.palette().color(QPalette.Highlight)
            highlight.setAlpha(60)
            return QBrush(highlight)
        if role == INDENT_ROLE:
            return location.group is not None
        return None

    def get_locations(self):
        return self.locations

    def findRowById(self, target_id):
        """Find the row of a location or group by its id; -1 if absent or in a collapsed group."""
        for row, entry in enumerate(self._rows):
            if getattr(entry, "lid", None) == target_id or getattr(entry, "gid", None) == target_id:
                return row
        return -1

    def get_location_by_id(self, target_id):
        return self.locations.loc_by_id(target_id)

    # Changing
    def setLocations(self, locations):
        self.locations = locations
        self._rebuild()

    def setHovered(self, location_id):
        """Highlight the location whose marker is hovered on the map (None for none)."""
        if location_id == self.hovered_id:
            return
        rows = [self.findRowById(i) for i in (self.hovered_id, location_id) if i]
        self.hovered_id = location_id
        for row in rows:
            if row != -1:
                index = self.index(row, 0)
                self.dataChanged.emit(index, index, [Qt.BackgroundRole])

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

    def updateNote(self, index: QModelIndex, new_note):
        """Set the note of the entry at index, and notify the views."""
        entry = self.getEntry(index)
        if entry is None:
            logger.error("Invalid index.")
            return
        entry.note = new_note
        self.dataChanged.emit(index, index)
        if isinstance(entry, Location) and entry.group is not None:
            # The group's title row shows its locations count, not its titles: nothing more to update
            pass

    updateLocationNote = updateNote

    def addLocation(self, location, group: Group = None):
        """Add a location, at the end of a group or of the ungrouped locations."""
        logger.info(f"LocationListModel.addLocation {location}")
        location.group = group.gid if group is not None else None
        if group is not None and group.collapsed:
            group.collapsed = False
        self.locations.append(location)
        self.locations.normalize_order()
        self._rebuild()

    def addGroup(self, group: Group):
        """Add a group, at the end of the list."""
        self.locations.add_group(group)
        self._rebuild()
        self.arranged.emit()

    def delete_item(self, index):
        """Delete the location or group of a row; a group's locations stay, ungrouped."""
        entry = self.getEntry(index)
        if isinstance(entry, Location):
            row = index.row()
            self.beginRemoveRows(QModelIndex(), row, row)
            self.locations.remove(entry)
            self._build_rows()
            self.endRemoveRows()
        elif isinstance(entry, Group):
            self.locations.remove_group(entry)
            self._rebuild()
            self.arranged.emit()

    def setCollapsed(self, group: Group, collapsed: bool):
        """Show or hide the locations of a group."""
        if group.collapsed != collapsed:
            group.collapsed = collapsed
            self._rebuild()
            self.arranged.emit()

    def clear(self):
        self.locations.clear()
        self._rebuild()

    # Drag and drop
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsDropEnabled
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
        if not isinstance(self.getEntry(index), TripNotes):  # the trip's notes stay first
            flags |= Qt.ItemIsDragEnabled
        return flags

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return [MIME_TYPE]

    def mimeData(self, indexes):
        """Serialize data to be dragged"""
        if not indexes:
            return None
        mime_data = super().mimeData(indexes)
        mime_data.setData(MIME_TYPE, str(indexes[0].row()).encode())
        return mime_data

    def dropMimeData(self, data, action, row, column, parent):
        """Move the dragged entry: Qt gives the insertion row for drops between rows,
        or the target row as parent for drops onto a row, which takes its place."""
        if action != Qt.MoveAction or not data.hasFormat(MIME_TYPE):
            return False
        source = int(data.data(MIME_TYPE).data().decode())
        entry = self.entry(source)
        if entry is None or isinstance(entry, TripNotes):
            return False
        if row != -1:
            destination = row
        elif parent.isValid():
            destination = parent.row() + 1 if parent.row() > source else parent.row()
        else:
            destination = self.rowCount()
        destination = max(destination, 1)  # nothing goes above the trip's notes
        if destination in (source, source + 1):
            return False  # dropped in place
        rows = list(self._rows)
        rows.insert(destination, entry)
        del rows[source + 1 if destination <= source else source]
        if isinstance(entry, Group):
            self._move_group(entry, rows)
        else:
            self._move_location(entry, rows, rows.index(entry))
        self._rebuild()
        self.arranged.emit()
        return True

    def _move_group(self, group, rows):
        groups = [e for e in rows if isinstance(e, Group)]
        self.locations.arrange(list(self.locations), groups)

    def _move_location(self, location, rows, position):
        # The location joins the section it was dropped in: the group of the
        # nearest group title or grouped location above it, or none
        section = None
        for entry in reversed(rows[:position]):
            if isinstance(entry, Group):
                section = entry
                break
            if isinstance(entry, Location):
                section = self.locations.group_by_id(entry.group)
                break
        location.group = section.gid if section is not None else None
        # Place it after the location above it in its section, if any, else first
        previous = rows[position - 1] if position > 0 else None
        ordered = [loc for loc in self.locations if loc is not location]
        if isinstance(previous, Location):
            ordered.insert(ordered.index(previous) + 1, location)
        else:
            members = [loc for loc in ordered if loc.group == location.group]
            ordered.insert(ordered.index(members[0]) if members else len(ordered), location)
        self.locations.arrange(ordered, self.locations.groups)


@lru_cache(maxsize=1)
def bold_font() -> QFont:
    font = QFont()
    font.setBold(True)
    return font


class EntryDelegate(QStyledItemDelegate):
    """Indents the locations of groups."""

    def paint(self, painter, option, index):
        if index.data(INDENT_ROLE):
            option = QStyleOptionViewItem(option)
            option.rect.adjust(GROUP_INDENT, 0, 0, 0)
        super().paint(painter, option, index)


class LocationListView(QListView):
    """The list of the trip's notes, groups and locations, next to the map.

    Emits entryClicked(entry) when an entry is clicked (TripNotes, Group or
    Location), locationClicked(Location) for locations, and locationHovered(id)
    when the mouse moves onto another location ("" when it leaves them).
    """

    entryClicked = Signal(object)
    locationClicked = Signal(object)  # Signal emitting the selected Location object
    locationHovered = Signal(str)
    # Shift-click on a location: a route from the selected location to it (issue #50)
    routeRequested = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LocationListModel()
        self.setModel(self.model)
        self.setItemDelegate(EntryDelegate(self))
        self.clicked.connect(self.on_item_clicked)
        self.doubleClicked.connect(self.on_item_double_clicked)
        self.setDragDropMode(QListView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIconSize(QSize(LIST_ICON_SIZE, LIST_ICON_SIZE))
        self.setMouseTracking(True)  # hover highlight of the markers
        self._list_hovered_id = None
        # Rebuilding the rows loses the selection: keep it
        self._selected_entry = None
        self.model.modelAboutToBeReset.connect(self._remember_selection)
        self.model.modelReset.connect(self._restore_selection)

    def _remember_selection(self):
        self._selected_entry = self.model.getEntry(self.currentIndex())

    def _restore_selection(self):
        row = self.model.rowOf(self._selected_entry) if self._selected_entry is not None else -1
        if row != -1:
            self.setCurrentIndex(self.model.index(row, 0))

    def dataChanged(self, topLeft, bottomRight, roles=()):
        super().dataChanged(topLeft, bottomRight, roles)
        # A hover highlight is not a change of the journey
        if list(roles) != [Qt.BackgroundRole]:
            self.model.locations.dirty.emit(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier:
            target = self.model.getLocation(self.indexAt(event.position().toPoint()))
            start = self.current_entry()
            if target is not None and isinstance(start, Location) and start is not target:
                # Keep the selection: the selected location is where the route starts
                self.routeRequested.emit(start, target)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        location = self.model.getLocation(self.indexAt(event.position().toPoint()))
        self.set_list_hover(location.lid if location is not None else None)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.set_list_hover(None)

    def set_list_hover(self, location_id):
        """Track the location under the mouse in the list, to highlight its marker."""
        if location_id != self._list_hovered_id:
            self._list_hovered_id = location_id
            self.locationHovered.emit(location_id or "")

    def setLocations(self, locations):
        self.model.setLocations(locations)

    def on_item_clicked(self, index):
        entry = self.model.getEntry(index)
        if entry is None:
            return
        self.entryClicked.emit(entry)
        if isinstance(entry, Location):
            self.locationClicked.emit(entry)

    def on_item_double_clicked(self, index):
        entry = self.model.getEntry(index)
        if isinstance(entry, Group):
            self.model.setCollapsed(entry, not entry.collapsed)

    def addLocation(self, location, group=None):
        self.model.addLocation(location, group)

    def locations(self):
        return self.model.get_locations()

    def current_entry(self):
        """The selected TripNotes, Group or Location, or None."""
        indexes = self.selectedIndexes()
        return self.model.getEntry(indexes[0]) if indexes else None

    def current_group(self):
        """The group of the selected entry: a group, or the group of a location; None otherwise."""
        entry = self.current_entry()
        if isinstance(entry, Group):
            return entry
        if isinstance(entry, Location):
            return self.model.locations.group_by_id(entry.group)
        return None

    def selectById(self, target_id):
        """Select a location or group by its id, expanding its group if needed."""
        location = self.model.get_location_by_id(target_id)
        if location is not None and location.group is not None:
            group = self.model.locations.group_by_id(location.group)
            if group is not None and group.collapsed:
                self.model.setCollapsed(group, False)
        row = self.model.findRowById(target_id)
        if row != -1:
            self.setCurrentIndex(self.model.index(row, 0))

    def select_entry(self, entry):
        row = self.model.rowOf(entry)
        if row != -1:
            self.setCurrentIndex(self.model.index(row, 0))

    def updateLocationNoteAtIndex(self, index, new_note):
        """Updates the note of the entry at a given QModelIndex."""
        self.model.updateNote(index, new_note)

    def deleteItemAtIndex(self, index):
        """Deletes the location or group at the given QModelIndex."""
        self.model.delete_item(index)

    def clear(self):
        """Clears all locations from the view."""
        self.model.clear()

    def get_location_by_id(self, target_id):
        return self.model.get_location_by_id(target_id)
