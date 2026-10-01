import logging
import nc_py_api
import sys

from PySide6.QtCore import QSettings, Qt, Slot
from PySide6.QtGui import QAction, QDoubleValidator, QIcon, QKeySequence, QTextCursor, QFont, QTextCharFormat, QTextFormat
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    )
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from geopy.exc import GeopyError
from geopy.geocoders import Nominatim
from importlib import resources
from pathlib import Path
from typing import Dict, List, Any





try:
    from .icon_picker import IconPickerWidget
    from .journey import Journey
    from .limited_color_picker import LimitedColorPicker
    from .location import Location
    from .location_list_view import LocationListView
    from .map_view import (DEFAULT_ZOOM, MapBridge, build_map_html, downplay_marker_js, highlight_marker_js, move_map_js,
                           update_marker_text_js)
    from .search_popup import SearchPopup
    from .config import ConfigDialog, load_nextcloud_password
    from .nextcloud_with_api import NextcloudFilePicker
    from .rename_popup import RenamePopup
    from .toolbar import ToolBar
    from .note_widget import NoteWidget
except ImportError:
    from icon_picker import IconPickerWidget
    from journey import Journey
    from limited_color_picker import LimitedColorPicker
    from location import Location
    from location_list_view import LocationListView
    from map_view import (DEFAULT_ZOOM, MapBridge, build_map_html, downplay_marker_js, highlight_marker_js, move_map_js,
                          update_marker_text_js)
    from search_popup import SearchPopup
    from config import ConfigDialog, load_nextcloud_password
    from nextcloud_with_api import NextcloudFilePicker
    from rename_popup import RenamePopup
    from toolbar import ToolBar
    from note_widget import NoteWidget

logger = logging.getLogger(__name__)

RECENT_FILES_KEY = "recentFiles"
MAX_RECENT_FILES = 10
NEXTCLOUD_PREFIX = "nextcloud:"
logging.basicConfig(level=logging.INFO)
logging.root.setLevel(logging.INFO)


class MapViewPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            logger.error(f"JS Console [{level}]: {message} (Line: {lineNumber}, Source: {sourceID})")
        else:  # if level == "JavaScriptConsoleMessageLevel.ErrorMessageLevel":
            logger.debug(f"JS Console [{level}]: {message} (Line: {lineNumber}, Source: {sourceID})")


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # self.current_location = None
        # QSettings initialization
        self.settings = QSettings("Kleag", "Otripy")

        self.channel = QWebChannel()
        self.map_bridge = MapBridge()
        self.channel.registerObject("mapBridge", self.map_bridge)
        self.map_bridge.mapClicked.connect(self.map_clicked)
        self.map_bridge.markerClicked.connect(self.handle_marker_click)
        # Last view of the map (latitude, longitude, zoom), kept when it is redrawn
        self.map_view_state = None
        self.map_bridge.viewChanged.connect(self.map_view_changed)

        self.setGeometry(100, 100, 800, 600)

        self.geolocator = Nominatim(user_agent="Otripy")

        self.current_file = None
        self.nc = None

        self.initUI()
        self.createMenu()
        self.update_map()
        self.dirty = False
        self.set_window_title(dirty=False)

    @Slot(bool)
    def set_window_title(self, dirty: bool):
        title = "Otripy"
        self.dirty = dirty
        if self.current_file:
            title = f"{title} - {self.current_file}"
        if dirty:
            title = f"* {title}"
        # logger.info(f"set_window_title {dirty}: {title}")
        self.setWindowTitle(title)

    def initUI(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # List view
        self.list_widget = LocationListView(self)
        self.list_widget.model.locations.dirty.connect(self.set_window_title)

        self.list_widget.locationClicked.connect(self.on_item_selected)
        # self.list_widget.setLocations(self.locations)

        # Main widget (Text editor for simplicity)
        self.map_page = MapViewPage()
        self.map_page.setWebChannel(self.channel)
        self.map_view = QWebEngineView()
        self.map_view.setPage(self.map_page)


        # Search interface : line edit + button at its right
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search…")
        self.search_entry.returnPressed.connect(self.search_location)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_location)
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.search_btn)

        # Search popup (floating list)
        self.search_popup = SearchPopup(self)

        # Buttons
        btn_layout = QHBoxLayout()

        lat_val = QDoubleValidator(-90, 90, 3)
        lat_val.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("Enter Latitude")
        self.lat_input.setValidator(lat_val)
        self.lat_input.setReadOnly(True)

        lon_val = QDoubleValidator(-180, 180, 3)
        lon_val.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.lon_input = QLineEdit()
        self.lon_input.setPlaceholderText("Enter Longitude")
        self.lon_input.setValidator(lon_val)
        self.lon_input.setReadOnly(True)

        btn_layout.addWidget(self.lat_input)
        btn_layout.addWidget(self.lon_input)

        self.note_input = NoteWidget(self)
        self.note_input.setPlaceholderText("Enter Note")
        self.note_input.textChanged.connect(self.note_changed)
        self.note_input.setAutoFormatting(QTextEdit.AutoFormatting.AutoAll)
        # self.add_button = QPushButton("Save Location", self)
        # self.add_button.clicked.connect(self.add_location)

        self.del_btn = QPushButton("Delete Location")
        self.del_btn.clicked.connect(self.delete_item)

        self.create_icons_toolbar()

        # Panels, resizable with splitters: the list on the left; on the right,
        # the map above the note
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.addWidget(self.list_widget)
        list_layout.addWidget(self.del_btn)

        note_panel = QWidget()
        note_layout = QVBoxLayout(note_panel)
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.addLayout(btn_layout)
        note_layout.addWidget(self.toolbar)
        note_layout.addWidget(self.note_input)

        self.map_splitter = QSplitter(Qt.Vertical)
        self.map_splitter.addWidget(self.map_view)
        self.map_splitter.addWidget(note_panel)
        self.map_splitter.setStretchFactor(0, 1)  # the map takes the extra height
        self.map_splitter.setSizes([500, 200])

        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.addLayout(search_layout)
        map_layout.addWidget(self.map_splitter)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(list_panel)
        self.main_splitter.addWidget(map_panel)
        self.main_splitter.setStretchFactor(1, 1)  # the map takes the extra width
        self.main_splitter.setSizes([250, 550])

        for splitter in (self.main_splitter, self.map_splitter):
            splitter.setChildrenCollapsible(False)
        self.restore_layout()

        layout.addWidget(self.main_splitter)
        central_widget.setLayout(layout)

    def restore_layout(self):
        """Restore the panel sizes saved by save_layout."""
        for key, splitter in (("window/mainSplitter", self.main_splitter), ("window/mapSplitter", self.map_splitter)):
            state = self.settings.value(key)
            if state is not None:
                splitter.restoreState(state)

    def save_layout(self):
        """Save the panel sizes in the settings, for the next start."""
        self.settings.setValue("window/mainSplitter", self.main_splitter.saveState())
        self.settings.setValue("window/mapSplitter", self.map_splitter.saveState())

    def createMenu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new)

        load_action = QAction("Open…", self)
        load_action.setShortcut(QKeySequence("Ctrl+O"))
        load_action.triggered.connect(self.load_file)

        load_nc_action = QAction("Open Nextcloud…", self)
        load_nc_action.setShortcut(QKeySequence("Ctrl+Alt+O"))
        load_nc_action.triggered.connect(self.load_nc_file)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_file)

        save_as_action = QAction("Save As…", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_file_as)

        save_as_nc_action = QAction("Save As Nextcloud…", self)
        save_as_nc_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        save_as_nc_action.triggered.connect(self.save_file_as_nc)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(load_action)
        file_menu.addAction(load_nc_action)
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self.update_recent_menu)
        self.update_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addAction(save_as_nc_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)
        # export_action = file_menu.addAction("Export as HTML Map…")
        # export_action.triggered.connect(self.export_as_html)

        config_menu = menu_bar.addMenu("Settings")

        # Configuration action
        config_action = QAction("Configure Otripy", self)
        config_action.triggered.connect(self.open_config_dialog)
        config_menu.addAction(config_action)

        # Clicking the map adds a location at once, unless this is checked (issue #30)
        self.confirm_locations_action = QAction("Confirm New Locations", self)
        self.confirm_locations_action.setCheckable(True)
        self.confirm_locations_action.setChecked(self.settings.value("map/confirmNewLocations", False, type=bool))
        self.confirm_locations_action.toggled.connect(
            lambda checked: self.settings.setValue("map/confirmNewLocations", checked))
        config_menu.addAction(self.confirm_locations_action)

    # def export_as_html(self):
    #     if not self.model or not getattr(self.model, "trip_data", None):
    #         QMessageBox.warning(self, "No Trip Loaded", "Please load a trip before exporting.")
    #         return
    #
    #     file_path, _ = QFileDialog.getSaveFileName(
    #         self,
    #         "Save HTML Map",
    #         str(Path.home() / "map.html"),
    #         "HTML Files (*.html)"
    #     )
    #     if not file_path:
    #         return
    #
    #     try:
    #         export_html(self.model.trip_data, Path(file_path))
    #         QMessageBox.information(self, "Export Complete", f"Map saved to:\n{file_path}")
    #     except Exception as e:
    #         QMessageBox.critical(self, "Export Failed", str(e))

    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """
        Main toolbar items map for convenience.
        """
        return [
            # # Text format
            {'type': 'action', 'weight': 7,
             'name': 'toolbar_toolbar_icon_header1',
             'text_icon': 'h1',
             'color': 'red',
             'label': 'Header1',
             'accessible_name': 'h1',
             'action': self.action_text_h1,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 7,
             'name': 'toolbar_toolbar_icon_header2',
             'text_icon': 'h2',
             'color': 'red',
             'label': 'Header2',
             'accessible_name': 'h2',
             'action': self.action_text_h2,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 7,
             'name': 'toolbar_toolbar_icon_header3',
             'text_icon': 'h3',
             'color': 'red',
             'label': 'Header3',
             'accessible_name': 'h3',
             'action': self.action_text_h3,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 7,
             'name': 'toolbar_toolbar_icon_color_bold',
             'system_icon': 'format-text-bold',
             'theme_icon': 'bold.svg',
             'color': 'red',
             'label': 'Bold',
             'accessible_name': 'bold',
             'action': self.action_text_bold,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 8,
             'name': 'toolbar_actions_label_italic',
             'system_icon': 'format-text-italic',
             'theme_icon': 'italic.svg',
             'color': 'red',
             'label': 'Italic',
             'accessible_name': 'italic',
             'action': self.action_text_italic,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 9,
             'name': 'toolbar_actions_label_underline',
             'system_icon': 'format-text-underline',
             'theme_icon': 'underline.svg',
             'color': 'red',
             'label': 'Underline',
             'accessible_name': 'underline',
             'action': self.action_text_underline,
             'switched_off_check': lambda: False},
            {'type': 'action', 'weight': 10,
             'name': 'toolbar_actions_label_strikethrough',
             'system_icon': 'format-text-strikethrough',
             'theme_icon': 'strikethrough.svg',
             'color': 'red',
             'label': 'Strikethrough',
             'accessible_name': 'strikethrough',
             'action': self.action_text_strikethrough,
             'switched_off_check': lambda: False},
            # {'type': 'action', 'weight': 11, 'name': 'toolbar_actions_label_blockquote',
            #  'system_icon': 'format-text-blockquote', 'theme_icon': 'quote.svg',
            #  'color': self.theme_helper.get_color('toolbar_icon_color_blockquote'),
            #  'label': self.lexemes.get('actions_label_blockquote', scope='toolbar'),
            #  'accessible_name': self.lexemes.get('actions_accessible_name_blockquote', scope='toolbar'),
            #  'action': self.action_text_blockquote, 'switched_off_check': lambda: self.get_mode() != Mode.EDIT},
            # {'type': 'delimiter'},
            {'type': 'action',
             'weight': 13,
             'name': 'toolbar_actions_marker_icon',
             'theme_icon': 'location-dot.svg',
             'color': 'red',
             'label': 'Marker',
             'accessible_name': 'marker',
             'action': self.action_marker_icon},
            {'type': 'action',
             'weight': 13,
             'name': 'toolbar_actions_label_color',
             'theme_icon': 'eye-dropper.svg',
             'color': 'red',
             'label': 'Color',
             'accessible_name': 'color',
             'action': self.action_marker_color_picker},
            # {'type': 'delimiter'},
        ]

    def action_text_h1(self):
        self.action_text_h(1)

    def action_text_h2(self):
        self.action_text_h(2)

    def action_text_h3(self):
        self.action_text_h(3)

    def action_text_h(self, level: int):
        cursor = self.note_input.textCursor()
        # cursor.beginEditBlock()
        blockFormat = cursor.blockFormat()

        # Ensure level is between 1 and 6
        level = max(1, min(level, 6))
        # logger.debug(f"action_text_h new level: {level}")

        current_level = blockFormat.headingLevel()
        # logger.debug(f"action_text_h cur level: {current_level}")

        level = 0 if current_level == level else level
        blockFormat.setHeadingLevel(level)

        cursor.setBlockFormat(blockFormat)
        self.note_input.setTextCursor(cursor)
        self.note_input.repaint()
        self.note_input.update()

        # H1 to H6: +3 to -2
        size_adjustment = 4 - level if level != 0 else 0
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if level else QFont.Normal)
        fmt.setProperty(QTextFormat.FontSizeAdjustment, size_adjustment)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.note_input.mergeCurrentCharFormat(fmt)

    def action_text_bold(self):
        cursor = self.note_input.textCursor()

        if not cursor.hasSelection():
            return  # Do nothing if there's no selected text

        char_format = cursor.charFormat()
        if char_format.fontWeight() == QFont.Bold:
            # If text is already bold, remove the bold
            char_format.setFontWeight(QFont.Normal)
        else:
            # If text is not bold, make it bold
            char_format.setFontWeight(QFont.Bold)
        cursor.mergeCharFormat(char_format)
        self.note_input.setTextCursor(cursor)

    def action_text_italic(self):
        cursor = self.note_input.textCursor()

        if not cursor.hasSelection():
            return  # Do nothing if there's no selected text

        char_format = cursor.charFormat()
        char_format.setFontItalic(not char_format.fontItalic())
        cursor.mergeCharFormat(char_format)
        self.note_input.setTextCursor(cursor)

    def action_text_underline(self):
        cursor = self.note_input.textCursor()

        if not cursor.hasSelection():
            return  # Do nothing if there's no selected text

        char_format = cursor.charFormat()
        char_format.setFontUnderline(not char_format.fontUnderline())
        cursor.mergeCharFormat(char_format)
        self.note_input.setTextCursor(cursor)

    def action_text_strikethrough(self):
        cursor = self.note_input.textCursor()

        if not cursor.hasSelection():
            return  # Do nothing if there's no selected text

        char_format = cursor.charFormat()
        char_format.setFontStrikeOut(not char_format.fontStrikeOut())
        cursor.mergeCharFormat(char_format)
        self.note_input.setTextCursor(cursor)

    def action_marker_color_picker(self):
        logger.info("action_marker_color_picker")
        selected_indexes = self.list_widget.selectedIndexes()
        if selected_indexes:
            selected_item = selected_indexes[0]
            if self.list_widget.model.getLocation(selected_item) is not None:
                color = LimitedColorPicker.get_color()
                if color is None:
                    return  # cancelled: keep the current color
                self.list_widget.model.setMarkerStyle(selected_item, color=color)
                self.update_map()
        else:
            logger.warning("Marker color picker hit while no location is selected")

        cursor = self.note_input.textCursor()

        if not cursor.hasSelection():
            return  # Do nothing if there's no selected text

        char_format = cursor.charFormat()
        # char_format.setFontStrikeOut(not char_format.fontStrikeOut())
        cursor.mergeCharFormat(char_format)
        self.note_input.setTextCursor(cursor)

    def action_marker_icon(self):
        marker_select_widget = IconPickerWidget(self)
        marker_select_widget.icon_selected.connect(self.marker_chosen)
        marker_select_widget.exec()

    def marker_chosen(self, icon_name):
        logger.info(f"Selected marker: {icon_name}")
        selected_indexes = self.list_widget.selectedIndexes()
        if selected_indexes:
            selected_item = selected_indexes[0]

            if self.list_widget.model.getLocation(selected_item) is not None:
                self.list_widget.model.setMarkerStyle(selected_item, marker=icon_name)
                self.update_map()
        else:
            logger.warning(f"Marker chosen {icon_name} while no location is selected")

    def get_toolbar_action_by_name(self, name):
        """
        Get particular action config by name.
        """
        for action in self.get_toolbar_actions():
            if 'name' in action and action['name'] == name:
                return action

    def create_icons_toolbar(self, refresh: bool = False) -> ToolBar:
        """
        Main toolbar with icons.
        """
        if refresh and hasattr(self, 'toolbar'):
            self.removeToolBar(self.toolbar)
        """
        Or Toolbar element:
        toolbar = self.addToolBar("Toolbar")
        """
        self.toolbar = ToolBar(
            parent=self,
            actions=self.get_toolbar_actions(),
            refresh=lambda: self.create_icons_toolbar(refresh=True)  # Action to call if refresh needed
        )

        return self.toolbar
        # self.addToolBar(self.toolbar)

    @Slot(float, float)
    def map_clicked(self, lat: float, lon: float):
        """Add a location where the map was clicked, after confirmation if the user asked for it."""
        self.add_location_at(lat, lon, confirm=self.confirm_locations_action.isChecked())

    def add_location_at(self, lat: float, lon: float, confirm: bool = False):
        """Add a location at the given coordinates, its note initialized with the address found there.

        With confirm, first ask the user, showing the address.
        """
        try:
            place = self.geolocator.reverse(f"{lat}, {lon}")
        except GeopyError as e:
            logger.warning(f"Reverse geocoding failed: {e}")
            place = None
        if confirm:
            where = place.address if place is not None else f"[{lat:.5f}, {lon:.5f}]"
            answer = QMessageBox.question(self, "New Location", f"Add a location here?\n\n{where}",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer != QMessageBox.Yes:
                return
        self.lat_input.setText(str(lat))
        self.lon_input.setText(str(lon))
        # The place name becomes the note title (its first paragraph)
        address = (place.address.replace(", ", "\n\n", 1) if place is not None
                   else f"Unknown place at [{lat}, {lon}]")
        self.note_input.textChanged.disconnect(self.note_changed)
        try:
            self.note_input.from_note({"markdown": address})
        finally:
            self.note_input.textChanged.connect(self.note_changed)
        self.add_location()

    @Slot()
    def note_changed(self):
        # logger.info(f"MapApp.note_changed")
        selected_indexes = self.list_widget.selectedIndexes()
        if selected_indexes:
            location = self.list_widget.model.getLocation(selected_indexes[0])
            old_label = location.label() if location is not None else None
            self.list_widget.updateLocationNoteAtIndex(selected_indexes[0], self.note_input.to_note())
            # The list shows the new title at once; the map's marker needs updating too
            if location is not None and location.label() != old_label:
                self.map_page.runJavaScript(update_marker_text_js(location))

    @Slot(float, float, int)
    def map_view_changed(self, lat: float, lon: float, zoom: int):
        self.map_view_state = (lat, lon, zoom)

    def update_map(self, fit_all: bool = False):
        """Redraw the map, keeping its current view; with fit_all, zoom it to show all the locations."""
        if fit_all:
            self.map_view_state = None
        self.map_page.setHtml(build_map_html(self.list_widget.locations(), fit_all=fit_all,
                                             view=self.map_view_state))

    def handle_marker_click(self, marker_id):
        """ Handle marker click events in Python. """
        logger.info(f"MapApp.handle_marker_click {marker_id}")
        self.list_widget.selectById(marker_id)
        for loc in self.list_widget.locations():
            if loc.lid == marker_id:
                self.on_item_selected(loc)

    def highlight_marker(self, marker_id):
        """Show a marker with the large red highlight icon."""
        self.map_page.runJavaScript(highlight_marker_js(marker_id))

    def downplay_marker(self, marker_id):
        """Restore a marker's own icon."""
        loc = self.list_widget.model.get_location_by_id(marker_id)
        if loc is not None:
            self.map_page.runJavaScript(downplay_marker_js(loc))

    def add_location(self):
        # logger.info(f"MapApp.add_location")
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            note = self.note_input.to_note()
            new_location = Location(lat=lat, lon=lon, note=note)
            self.list_widget.addLocation(new_location)
            # self.current_location = new_location
            self.update_map()
            self.handle_marker_click(new_location.lid)
        except ValueError:
            logger.error("Invalid latitude or longitude")

    def open_config_dialog(self):
        """Open the configuration dialog"""
        dialog = ConfigDialog(self.settings, self)
        dialog.exec()

    def confirm_discard(self) -> bool:
        """Return True if there are no unsaved changes or the user agrees to lose them."""
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Journey Modified",
            "Do you really want to lose your changes?",
            QMessageBox.Yes | QMessageBox.No)
        return answer == QMessageBox.Yes

    def set_journey(self, journey: Journey, current_file):
        """Show a newly loaded journey; current_file is a local path or a Nextcloud FsNode."""
        self.current_file = current_file
        self.list_widget.setLocations(journey)
        journey.dirty.connect(self.set_window_title)
        self.set_window_title(dirty=False)
        self.update_map(fit_all=True)
        self.remember_current_file()

    def new(self):
        if self.confirm_discard():
            self.set_journey(Journey(), None)

    def load_file(self):
        if not self.confirm_discard():
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open JSON File",
            "",
            "JSON Files (*.json);;All files (*.*)")
        if file_name:
            self.open_local_file(file_name)

    def open_local_file(self, file_name) -> bool:
        """Open a journey file, without asking about unsaved changes. Return True on success."""
        try:
            journey = Journey.from_file(file_name)
        except (OSError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
            return False
        self.set_journey(journey, file_name)
        return True

    def connect_nextcloud(self) -> bool:
        """Connect to the Nextcloud server configured in the settings, if not done yet."""
        if self.nc is not None:
            return True
        base_url = self.settings.value("nextcloud/url", "")
        username = self.settings.value("nextcloud/username", "")
        password = load_nextcloud_password(self.settings)
        if not base_url or not username or not password:
            QMessageBox.critical(
                self,
                "Error",
                "Please set Nextcloud data in settings before connecting.")
            return False
        try:
            self.nc = nc_py_api.Nextcloud(nextcloud_url=base_url,
                                          nc_auth_user=username,
                                          nc_auth_pass=password)
        except nc_py_api.NextcloudException as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error connecting to Nextcloud:\n\n{e}")
            return False
        return True

    def load_nc_file(self):
        if not self.confirm_discard() or not self.connect_nextcloud():
            return
        file_picker = NextcloudFilePicker(self.nc, self)
        if file_picker.exec() != QDialog.DialogCode.Accepted:
            return
        selected_file = file_picker.get_selected_file()
        if selected_file:
            self.open_nc_file(selected_file)

    def open_nc_file(self, path) -> bool:
        """Open a journey file from Nextcloud, without asking about unsaved changes. Return True on success."""
        try:
            # keep the nc_py_api FsNode: its etag detects remote changes on save
            node = self.nc.files.by_path(path)
            journey = Journey.from_json_str(self.nc.files.download(node).decode("utf-8"))
        except (nc_py_api.NextcloudException, ValueError, KeyError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
            return False
        self.set_journey(journey, node)
        return True

    # Recent files (issue #11): local paths, and Nextcloud paths with a prefix
    def recent_files(self) -> List[str]:
        files = self.settings.value(RECENT_FILES_KEY, [])
        return [files] if isinstance(files, str) else list(files or [])

    def remember_current_file(self):
        """Put the current file first in the recent files."""
        if not self.current_file:
            return
        entry = (NEXTCLOUD_PREFIX + self.current_file.user_path if isinstance(self.current_file, nc_py_api.FsNode)
                 else str(Path(self.current_file).resolve()))
        files = [entry] + [f for f in self.recent_files() if f != entry]
        self.settings.setValue(RECENT_FILES_KEY, files[:MAX_RECENT_FILES])

    def forget_recent_file(self, entry):
        self.settings.setValue(RECENT_FILES_KEY, [f for f in self.recent_files() if f != entry])

    def update_recent_menu(self):
        """Rebuild the Open Recent menu from the settings."""
        self.recent_menu.clear()
        files = self.recent_files()
        for entry in files:
            if entry.startswith(NEXTCLOUD_PREFIX):
                label = f"{entry[len(NEXTCLOUD_PREFIX):]} (Nextcloud)"
            else:
                label = entry
            action = self.recent_menu.addAction(label)
            action.triggered.connect(lambda checked=False, entry=entry: self.open_recent_file(entry))
        if files:
            self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Clear Recent Files")
        clear_action.setEnabled(bool(files))
        clear_action.triggered.connect(lambda: self.settings.setValue(RECENT_FILES_KEY, []))

    def open_recent_file(self, entry) -> bool:
        if not self.confirm_discard():
            return False
        if entry.startswith(NEXTCLOUD_PREFIX):
            if not self.connect_nextcloud():
                return False
            opened = self.open_nc_file(entry[len(NEXTCLOUD_PREFIX):])
        else:
            opened = self.open_local_file(entry)
        if not opened:
            self.forget_recent_file(entry)
        return opened

    def save_file(self) -> bool:
        """Save to the current file, asking for one if needed. Return True if the journey was saved."""
        if not self.current_file:
            return self.save_file_as()
        saved = (self.save_nc_file() if isinstance(self.current_file, nc_py_api.FsNode)
                 else self.save_local_file(self.current_file))
        if saved:
            self.remember_current_file()  # may have been saved under a new name
        return saved

    def save_nc_file(self) -> bool:
        data = self.list_widget.locations().to_json_str()
        try:
            remote_node = self.nc.files.by_id(self.current_file.file_id)
            if remote_node is not None and remote_node.etag == self.current_file.etag:
                self.current_file = self.nc.files.upload(self.current_file, data)
                choice = None
            else:
                # The file changed (or vanished) on the server since it was opened (issue #10)
                choice = self.ask_save_conflict(self.current_file.user_path, deleted=remote_node is None)
            if choice == "cancel":
                return False
            if choice == "overwrite":
                self.current_file = self.nc.files.upload(self.current_file.user_path, data)
            elif choice == "rename":
                popup = RenamePopup(self, self.current_file.user_path)
                if not popup.exec():
                    return False
                new_name = popup.line_edit.text().strip()
                if self.nc_file_exists(new_name):
                    QMessageBox.critical(self, "Error", f"File {new_name} already exists. Abort.")
                    return False
                self.current_file = self.nc.files.upload(new_name, data)
        except nc_py_api.NextcloudException as e:
            QMessageBox.critical(self, "Error", f"Failed to save file on Nextcloud: {e}")
            return False
        self.list_widget.locations().clean()
        return True

    def ask_save_conflict(self, path: str, deleted: bool) -> str:
        """Ask what to do with a Nextcloud file changed or deleted since it was opened.

        Return "rename" (save under another name), "overwrite" or "cancel".
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("File Changed on Nextcloud")
        happened = "was deleted" if deleted else "was changed by someone else"
        box.setText(f"{path} {happened} since you opened it.")
        box.setInformativeText("Save your version under another name, or replace the file with it?")
        rename = box.addButton("Save As…", QMessageBox.AcceptRole)
        overwrite = box.addButton("Overwrite", QMessageBox.DestructiveRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(rename)
        box.exec()
        return {rename: "rename", overwrite: "overwrite"}.get(box.clickedButton(), "cancel")

    def nc_file_exists(self, path) -> bool:
        try:
            self.nc.files.by_path(path)
        except nc_py_api.NextcloudException:
            return False
        return True

    def save_file_as(self) -> bool:
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Save JSON File",
                                                   "",
                                                   "JSON Files (*.json)")
        if not file_name:
            return False
        if not self.save_local_file(file_name):
            return False
        self.current_file = file_name
        self.set_window_title(dirty=False)
        self.remember_current_file()
        return True

    def save_file_as_nc(self) -> bool:
        """Save the journey to a new file on Nextcloud. Return True if it was saved."""
        if not self.connect_nextcloud():
            return False
        file_picker = NextcloudFilePicker(self.nc, self, save=True)
        if file_picker.exec() != QDialog.DialogCode.Accepted:
            return False
        path = file_picker.get_selected_file()
        try:
            if self.nc_file_exists(path):
                answer = QMessageBox.question(
                    self, "File Exists", f"{path} already exists on Nextcloud. Replace it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return False
            self.current_file = self.nc.files.upload(path, self.list_widget.locations().to_json_str())
        except nc_py_api.NextcloudException as e:
            QMessageBox.critical(self, "Error", f"Failed to save file on Nextcloud: {e}")
            return False
        self.list_widget.locations().clean()
        self.set_window_title(dirty=False)
        self.remember_current_file()
        return True

    def save_local_file(self, file_name) -> bool:
        try:
            self.list_widget.locations().save(file_name)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
            return False
        self.list_widget.locations().clean()
        return True

    def delete_item(self):
        selected_indexes = self.list_widget.selectedIndexes()
        if selected_indexes:
            selected_item = selected_indexes[0]
            self.list_widget.deleteItemAtIndex(selected_item)
            self.update_map()

    def on_item_selected(self, loc: Location):
        # logger.info(f"MapApp.on_item_selected {loc}")
        self.lat_input.setText(str(loc.lat))
        self.lon_input.setText(str(loc.lon))
        self.note_input.textChanged.disconnect()
        self.note_input.from_note(loc.note)
        self.note_input.textChanged.connect(self.note_changed)
        # logger.info(f"MapApp.on_item_selected {item} after from_note")
        for a_loc in self.list_widget.locations():
            (self.highlight_marker(loc.lid) if loc.lid == a_loc.lid
             else self.downplay_marker(a_loc.lid))
        self.map_page.runJavaScript(move_map_js(loc.lat, loc.lon))

    def closeEvent(self, event):
        self.save_layout()
        if not self.dirty:
            event.accept()
            return
        reply = QMessageBox.question(self, 'Journey Modified',
                                     'You have unsaved changes. Do you want to save them?',
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)
        if reply == QMessageBox.Discard or (reply == QMessageBox.Save and self.save_file()):
            event.accept()
        else:
            event.ignore()  # Cancelled, or the save failed or was cancelled: keep the window open

    def search_location(self):
        # logger.info(f"MapApp.search_location {self.search_entry.text()}")
        query = self.search_entry.text().strip()
        if not query:
            self.search_popup.hide()
            return
        try:
            locations = self.geolocator.geocode(query, exactly_one=False)
        except GeopyError as e:
            self.search_popup.hide()
            QMessageBox.critical(self, "Error", f"Search failed: {e}")
            return

        # logger.info(f"Found: {locations}")

        self.search_popup.show_popup(locations, self.search_entry)
        # # Show popup if results exist
        # if locations:
        #     self.search_popup.show_popup(locations, self.search_entry)
        # else:
        #     self.search_popup.hide()

    def handle_selected_location(self, location):
        """Handle the selected location"""
        # logger.info(f"Selected: {location}")
        # The place may be anywhere: center the redrawn map on it, at the current zoom
        zoom = self.map_view_state[2] if self.map_view_state is not None else DEFAULT_ZOOM
        self.map_view_state = (location.latitude, location.longitude, zoom)
        self.add_location_at(location.latitude, location.longitude)


def main():
    if sys.argv[1:2] == ["--self-test"]:
        try:
            from .self_test import run
        except ImportError:
            from self_test import run
        sys.exit(run(sys.argv[2] if len(sys.argv) > 2 else None))
    app = QApplication(sys.argv)
    app_icon = QIcon()
    for size in (16, 32, 64, 128, 256, 512):
        app_icon.addFile(str(resources.files("otripy.resources") / f"icon-{size}.png"))
    app.setWindowIcon(app_icon)
    window = MapApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
