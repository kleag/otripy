import folium
import io
import json
import logging
import nc_py_api
import os
import sys

from PySide6.QtCore import QSettings, QUrl, QObject, Signal, Slot
from PySide6.QtGui import QAction, QDoubleValidator, QKeySequence, QTextCursor, QFont, QTextCharFormat, QTextFormat
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    )
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from branca.element import Element
from folium.elements import *
from geopy.geocoders import Nominatim
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Any

try:
    from .icon_picker import IconPickerWidget
    from .journey import Journey
    from .location import Location
    from .location_list_view import LocationListView
    from .search_popup import SearchPopup
    from .config import ConfigDialog
    from .nextcloud_with_api import NextcloudFilePicker
    from .rename_popup import RenamePopup
    from .toolbar import ToolBar
    from .note_widget import NoteWidget
except ImportError:
    from icon_picker import IconPickerWidget
    from journey import Journey
    from location import Location
    from location_list_view import LocationListView
    from search_popup import SearchPopup
    from config import ConfigDialog
    from nextcloud_with_api import NextcloudFilePicker
    from rename_popup import RenamePopup
    from toolbar import ToolBar
    from note_widget import NoteWidget

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.root.setLevel(logging.INFO)


class MarkerHandler(QObject):
    """ Exposes a slot to receive marker click events from JavaScript. """
    markerClicked = Signal(str)  # Signal to send marker ID when clicked

    @Slot(str)
    def on_marker_clicked(self, marker_id):
        # logger.info(f"Marker clicked: {marker_id}")  # Handle click event in Python
        self.markerClicked.emit(marker_id)  # Emit the signal for further handling


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
        self.marker_handler = MarkerHandler()
        self.channel.registerObject("markerHandler", self.marker_handler)
        self.channel.registerObject("pyObj", self)

        # Connect markerClicked signal to a Python slot
        self.marker_handler.markerClicked.connect(self.handle_marker_click)

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

        self.list_widget.setMaximumWidth(300)
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
        self.note_input.setMaximumHeight(200)
        self.note_input.setPlaceholderText("Enter Note")
        self.note_input.textChanged.connect(self.note_changed)
        self.note_input.setAutoFormatting(QTextEdit.AutoFormatting.AutoAll)
        # self.add_button = QPushButton("Save Location", self)
        # self.add_button.clicked.connect(self.add_location)

        self.del_btn = QPushButton("Delete Location")
        self.del_btn.clicked.connect(self.delete_item)

        self.create_icons_toolbar()
        ctrl_layout = QVBoxLayout()
        ctrl_layout.addLayout(search_layout)
        ctrl_layout.addWidget(self.map_view)
        ctrl_layout.addLayout(btn_layout)
        ctrl_layout.addWidget(self.toolbar)
        ctrl_layout.addWidget(self.note_input)
        # ctrl_layout.addWidget(self.add_button)

        list_layout = QVBoxLayout()
        list_layout.addWidget(self.list_widget)
        list_layout.addWidget(self.del_btn)

        # Layout arrangement
        main_layout = QHBoxLayout()
        main_layout.addLayout(list_layout, 1)
        main_layout.addLayout(ctrl_layout, 2)

        layout.addLayout(main_layout)
        # layout.addLayout(ctrl_layout)

        central_widget.setLayout(layout)

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

        # TODO Implement Save As on Nextcloud
        # save_as_nc_action = QAction("Save As Nextcloud…", self)
        # save_as_nc_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        # save_as_nc_action.triggered.connect(self.save_file_as_nc)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(load_action)
        file_menu.addAction(load_nc_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        # file_menu.addAction(save_as_nc_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        config_menu = menu_bar.addMenu("Settings")

        # Configuration action
        config_action = QAction("Configure Otripy", self)
        config_action.triggered.connect(self.open_config_dialog)
        config_menu.addAction(config_action)

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
             'action': self.action_text_color_picker},
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

    def action_text_color_picker(self):
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

            location = self.list_widget.model.getLocation(selected_item)
            if location is not None:
                location.marker = icon_name
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

    @Slot(dict)
    def receiveData(self, data):
        # logger.debug(f"MapApp.receiveData Received from JS: {data}")
        data["note"] = ""
        try:
            self.note_input.textChanged.disconnect()
            self.lat_input.setText(str(data["lat"]).strip())
            self.lon_input.setText(str(data["lon"]).strip())
            location = self.geolocator.reverse(f"{data["lat"]}, {data["lon"]}")
            address = location.address.replace(", ", "\n", 1) if location is not None else f"Unknown place at [{self.lat_input.text().strip()}, {self.lon_input.text().strip()}]"
            note = {"markdown": address}
            self.note_input.from_note(note)
            self.note_input.textChanged.connect(self.note_changed)
            self.add_location()
        except json.JSONDecodeError as e:
            pass

    @Slot()
    def note_changed(self):
        # logger.info(f"MapApp.note_changed")
        selected_indexes = self.list_widget.selectedIndexes()
        if selected_indexes:
            self.list_widget.updateLocationNoteAtIndex(selected_indexes[0], self.note_input.to_note())

    def update_map(self):
        # Default location (Paris)
        location = [48.8566, 2.3522]
        if self.list_widget.locations():
            location = self.list_widget.locations()[-1].location()
        m = folium.Map(location=location, zoom_start=12)
        m.get_root().html.add_child(
            JavascriptLink('qrc:///qtwebchannel/qwebchannel.js'))
        m.get_root().html.add_child(
            JavascriptLink('https://cdnjs.cloudflare.com/ajax/libs/leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.min.js'))

        script = """
        function moveMap(lat, lng, zoom) {
            let mapElement = document.querySelector("div[id^='map_']");
            if (mapElement) {
                let mapId = mapElement.id; // Get the actual map ID
                let map = window[mapId]; // Folium stores the map as a global variable with its ID
                map.setView([lat, lng], zoom);
            }
        }

        pywebchannel = new QWebChannel(qt.webChannelTransport, function(channel) {
            var pyObj = channel.objects.pyObj;
            if (pyObj) {
                //pyObj.receiveData("Data from JS!");
            } else {
                console.error("pyObj is not available.");
            }
            var markerHandler = channel.objects.markerHandler;
            if (markerHandler) {
                //pyObj.receiveData("Data from JS!");
            } else {
                console.error("markerHandler is not available.");
            }
        });

        document.addEventListener("DOMContentLoaded", function() {
            window.markerMap = {};
            let mapElement = document.querySelector("div[id^='map_']");
            if (mapElement) {
                let mapId = mapElement.id; // Get the actual map ID
                let map = window[mapId]; // Folium stores the map as a global variable with its ID
                map.on("click", function(event) {

                    let lat = event.latlng.lat;
                    let lon = event.latlng.lng;
                    pywebchannel.objects.pyObj.receiveData({"lat": lat, "lon": lon});
                });
                """
        for loc in self.list_widget.locations():
            logger.info(f"Adding location to map: {repr(loc)}")
            tooltip = loc.label()
            popup = loc.to_html()
            if loc.marker is not None:
                icon = f"""
                var icon = L.AwesomeMarkers.icon({{
                    icon: 'fa-{loc.marker}',  // Icône FontAwesome (ex: fa-coffee, fa-car, fa-bicycle)
                    markerColor: '{loc.color if loc.color is not None else "blue"}', // Couleurs disponibles : red, blue, green, orange, yellow, purple, darkred, lightred, darkblue, lightblue, darkgreen, lightgreen, cadetblue, white, pink, gray, black
                    prefix: 'fa'        // Indique que l'on utilise FontAwesome
                }});
                """
                script += icon
                script += f"""
                var marker = L.marker([{loc.lat}, {loc.lon}], {{ icon: icon }}).addTo(map).bindTooltip("{tooltip}", {{permanent: false}}).bindPopup("{popup}");
                """
            else:
                script += f"""
                var marker = L.marker([{loc.lat}, {loc.lon}]).addTo(map).bindTooltip("{tooltip}", {{permanent: false}}).bindPopup("{popup}");
                """
            script += f"""
            window.markerMap["{loc.lid}"] = marker;
            marker.on("click", function() {{
                if (pywebchannel.objects.markerHandler) {{
                    pywebchannel.objects.markerHandler.on_marker_clicked("{loc.lid}");
                }}
            }});
            """
        script += """
            }
        });
        """
        m.get_root().script.add_child(Element(script))

        m.add_child(folium.ClickForMarker(popup="Click location"))

        data = io.BytesIO()
        m.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_page.setHtml(html)

    def handle_marker_click(self, marker_id):
        """ Handle marker click events in Python. """
        logger.info(f"MapApp.handle_marker_click {marker_id}")
        self.list_widget.selectById(marker_id)
        for loc in self.list_widget.locations():
            if loc.lid == marker_id:
                self.on_item_selected(loc)

    def highlight_marker(self, marker_id):
        """ Change marker color dynamically without modifying tooltip """
        logger.info(f"MapApp.highlight_marker {marker_id}")
        js_code = f"""
        if (window.markerMap["{marker_id}"]) {{
            window.markerMap["{marker_id}"].setIcon(
                L.icon({{
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
                    iconSize: [35, 55],  // Larger icon
                    iconAnchor: [17, 54],
                    popupAnchor: [1, -34],
                }})
            );
        }}
        """
        self.map_page.runJavaScript(js_code)

    def downplay_marker(self, marker_id):
        """ Change marker color dynamically without modifying tooltip """
        logger.info(f"MapApp.downplay_marker {marker_id}")
        loc = self.list_widget.model.get_location_by_id(marker_id)
        if loc and loc.marker is not None:
            icon_js = f"""
            var icon = L.AwesomeMarkers.icon({{
                icon: 'fa-{loc.marker}',  // Icône FontAwesome (ex: fa-coffee, fa-car, fa-bicycle)
                markerColor: '{loc.color if loc.color is not None else "blue"}', // Couleurs disponibles : red, blue, green, orange, yellow, purple, darkred, lightred, darkblue, lightblue, darkgreen, lightgreen, cadetblue, white, pink, gray, black
                prefix: 'fa'        // Indique que l'on utilise FontAwesome
            }});
            """
        else:
            icon_js = f"""var icon = new L.Icon.Default;"""
        js_code = f"""
        {icon_js}
        if (window.markerMap["{marker_id}"]) {{
            window.markerMap["{marker_id}"].setIcon(icon);
        }}
        """
        self.map_page.runJavaScript(js_code)

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

    def new(self):
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Journey Modified",
                "Do you really want to lose your changes?",
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
        self.current_file = None
        self.list_widget.clear()
        self.update_map()

    def load_file(self):
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Journey Modified",
                "Do you really want to lose your changes?",
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open JSON File",
            "",
            "JSON Files (*.json);;All files (*.*)")
        if file_name:
            try:
                with open(file_name, "r") as file:
                    json_str = file.read()
                    self.list_widget.clear()
                    # Complete missing data
                    self.current_file = file_name
                    self.list_widget.setLocations(Journey.from_json_str(json_str))
                    self.list_widget.model.locations.dirty.connect(self.set_window_title)
                    self.set_window_title(dirty=False)
                    self.update_map()
            except Exception as e:
                QMessageBox.critical(self,
                                     "Error",
                                     f"Failed to load file: {str(e)}")

    def load_nc_file(self):
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Journey Modified",
                "Do you really want to lose your changes?",
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
        if self.nc is None:
            base_url = self.settings.value("nextcloud/url", "")
            username = self.settings.value("nextcloud/username", "")
            password = self.settings.value("nextcloud/password", "")
            if not base_url or not username or not password:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Please set Nextcloud data in settings before connecting.")
                return
            try:
                self.nc = nc_py_api.Nextcloud(nextcloud_url=base_url,
                                            nc_auth_user=username,
                                            nc_auth_pass=password)
                # logger.info(f"nc capabilities: {self.nc.capabilities}")
            except nc_py_api.NextcloudException as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error connecting to Nextcloud:\n\n{e}")
                return
        file_picker = NextcloudFilePicker(self.nc, self)
        if file_picker.exec() == QDialog.DialogCode.Accepted:
            selected_file = file_picker.get_selected_file()
            if selected_file:
                # logger.info(f"MapApp.load_nc_file got {selected_file}")
                node = self.nc.files.by_path(selected_file)
                json_bytes = self.nc.files.download(selected_file)
                # Convert bytes to a string
                json_str = json_bytes.decode('utf-8')

                # Complete missing data
                self.list_widget.clear()
                self.current_file = node  # keep nc_py_api FsNode instead of string
                self.list_widget.setLocations(Journey.from_json_str(json_str))
                self.list_widget.model.locations.dirty.connect(self.set_window_title)
                self.set_window_title(dirty=False)
                self.update_map()

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
        elif type(self.current_file) == nc_py_api.FsNode:
            locations = [loc.to_dict() for loc in self.list_widget.locations()]
            data = json.dumps(locations, indent=4)
            file_id  = self.current_file.file_id
            current_remote_node = self.nc.files.by_id(file_id)
            if current_remote_node.etag != self.current_file.etag:
                popup = RenamePopup(self, self.current_file.user_path)
                if popup.exec():
                    new_name = popup.line_edit.text().strip()

                    #  by_path will raise an exception if the file does not already exist as we wan
                    try:
                        self.nc.files.by_path(new_name)
                        QMessageBox.critical(self, "Error", f"File {new_name} already exist. Abort.")
                        return
                    except nc_py_api.NextcloudException as e:
                        self.current_file = self.nc.files.upload(new_name, data)
                        return
                else:
                    return
            else:
                self.current_file = self.nc.files.upload(self.current_file, data)
        else:
            self.write_to_file(self.current_file)
        self.list_widget.model.locations.clean()

    def save_file_as(self):
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Save JSON File",
                                                   "",
                                                   "JSON Files (*.json)")
        if file_name:
            self.current_file = file_name
            self.write_to_file(file_name)
        self.list_widget.model.locations.clean()

    def save_file_as_nc(self):
        logger.error(f"MapApp.save_file_as_nc NOT IMPLEMENTED")
        pass

    def write_to_file(self, file_name):
        try:
            # locations = [loc.to_dict() for loc in self.list_widget.locations()]
            with open(file_name, "w") as file:
                self.list_widget.locations().write_to_file(file)
                # json.dump(locations, file, indent=4)
        except Exception as e:
            QMessageBox.critical(self,
                                 "Error",
                                 f"Failed to save file: {str(e)}")

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
        js_code = f"moveMap({loc.lat}, {loc.lon});"
        self.map_page.runJavaScript(js_code)

    def close(self):
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Journey Modified",
                "Do you really want to lose your changes?",
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
        QApplication.quit()

    def closeEvent(self, event):
        if self.dirty:
            reply = QMessageBox.question(self, 'Journey Modified',
                                         'You have unsaved changes. Do you want to save them?',
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                         QMessageBox.Save)
            if reply == QMessageBox.Save:
                # Handle saving here
                logger.info("Saving changes...")
                self.save_file()
                event.accept()  # Close the window after saving
            elif reply == QMessageBox.Discard:
                event.accept()  # Close the window without saving
            else:
                event.ignore()  # Ignore the close event to keep the window open
        else:
            event.accept()  # No unsaved changes, just close the window

    def search_location(self):
        # logger.info(f"MapApp.search_location {self.search_entry.text()}")
        query = self.search_entry.text().strip()
        if not query:
            self.search_popup.hide()
            return
        locations = self.geolocator.geocode(query, exactly_one=False)

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
        self.receiveData({"lat": location.latitude, "lon": location.longitude})


def main():
    # sys.argv.append("--disable-web-security")
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
