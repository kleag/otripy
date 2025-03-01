import folium
import io
import json
import logging
import nc_py_api
import os
import sys

from PySide6.QtCore import QSettings, QUrl, QObject, Signal, Slot
from PySide6.QtGui import QAction, QDoubleValidator, QKeySequence
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

try:
    from .journey import Journey
    from .location import Location
    from .search_popup import SearchPopup
    from .config import ConfigDialog
    from .nextcloud_with_api import NextcloudFilePicker
    from .nextcloud_with_api import NextcloudFilePicker
    from .rename_popup import RenamePopup
except ImportError:
    from journey import Journey
    from location import Location
    from search_popup import SearchPopup
    from config import ConfigDialog
    from nextcloud_with_api import NextcloudFilePicker
    from rename_popup import RenamePopup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.root.setLevel(logging.DEBUG)


class MarkerHandler(QObject):
    """ Exposes a slot to receive marker click events from JavaScript. """
    markerClicked = Signal(str)  # Signal to send marker ID when clicked

    @Slot(str)
    def on_marker_clicked(self, marker_id):
        logger.info(f"Marker clicked: {marker_id}")  # Handle click event in Python
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
        # QSettings initialization
        self.settings = QSettings("Kleag", "OpenTripPlan")

        self.channel = QWebChannel()
        self.marker_handler = MarkerHandler()
        self.channel.registerObject("markerHandler", self.marker_handler)
        self.channel.registerObject("pyObj", self)

        # Connect markerClicked signal to a Python slot
        self.marker_handler.markerClicked.connect(self.handle_marker_click)

        self.setWindowTitle("Open Trip Planner")
        self.setGeometry(100, 100, 800, 600)

        self.geolocator = Nominatim(user_agent="OpenTripPlan")

        self.current_file = None
        self.locations = Journey()
        self.nc = None

        self.initUI()
        self.createMenu()
        self.update_map()

    def initUI(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # List view
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(300)
        self.list_widget.itemClicked.connect(self.on_item_selected)

        # Main widget (Text editor for simplicity)
        self.map_page = MapViewPage()
        self.map_page.setWebChannel(self.channel)
        self.map_view = QWebEngineView()
        self.map_view.setPage(self.map_page)


        # Search interface : line edit + button at its right
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search…")
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

        self.note_input = QTextEdit(self)
        self.note_input.setMaximumHeight(200)
        self.note_input.setPlaceholderText("Enter Note")
        self.note_input.textChanged.connect(self.note_changed)
        # self.add_button = QPushButton("Save Location", self)
        # self.add_button.clicked.connect(self.add_location)

        self.del_btn = QPushButton("Delete Location")
        self.del_btn.clicked.connect(self.delete_item)

        ctrl_layout = QVBoxLayout()
        ctrl_layout.addLayout(search_layout)
        ctrl_layout.addWidget(self.map_view)
        ctrl_layout.addLayout(btn_layout)
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

    @Slot(dict)
    def receiveData(self, data):
        logger.debug(f"MapApp.receiveData Received from JS: {data}")
        data["note"] = ""
        try:
            if self.list_widget.currentItem() is not None:
                current_item = self.list_widget.currentItem()
                index = self.list_widget.row(current_item)
                self.downplay_marker(self.locations[index])
            self.list_widget.setCurrentItem(None)
            self.lat_input.setText(str(data["lat"]))
            self.lon_input.setText(str(data["lon"]))
            location = self.geolocator.reverse(f"{data["lat"]}, {data["lon"]}")
            address = location.address.replace(", ", "\n", 1)

            self.note_input.setText(address)
            self.add_location()
        except json.JSONDecodeError as e:
            pass

    @Slot()
    def note_changed(self):
        logger.info(f"MapApp.note_changed")
        selected_item = self.list_widget.currentItem()
        if selected_item:
            index = self.list_widget.row(selected_item)
            self.locations[index].note = self.note_input.toPlainText()
            lat = str(self.locations[index].lat)
            lon = str(self.locations[index].lon)
            label = self.locations[index].label()
            selected_item.setText(f"{label}: {lat}, {lon}")


    def update_map(self):
        # Default location (Paris)
        location = [48.8566, 2.3522]
        if self.locations:
            location = self.locations[-1].location()
        m = folium.Map(location=location, zoom_start=12)
        m.get_root().html.add_child(
            JavascriptLink('qrc:///qtwebchannel/qwebchannel.js'))


        # # Convert locations to JSON format
        # locations_json = json.dumps([
        #     {
        #         "id": loc["id"],
        #         "lat": loc["lat"],
        #         "lon": loc["lon"],
        #         "tooltip": loc["note"].split("\n")[0],
        #         "popup": loc["note"].replace("\n", "<br>")
        #     }
        #     for loc in self.locations
        # ])
        #
        # # Inject `__LOCATIONS__` **before** loading map_script.js
        # script = f"var __LOCATIONS__ = {locations_json};"
        # logger.debug(f"Injecting {script}")
        # m.get_root().script.add_child(Element(script))
        # script_path = os.path.abspath("map_script.js")
        # script_url = f"file://{script_path}"
        # m.get_root().script.add_child(JavascriptLink(script_url))

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
        for loc in self.locations:
            tooltip = loc.label()
            popup = loc.to_html()
            script += f"""
            var marker = L.marker([{loc.lat}, {loc.lon}]).addTo(map).bindTooltip("{tooltip}", {{permanent: false}}).bindPopup("{popup}");
            window.markerMap["{loc.id}"] = marker;
            marker.on("click", function() {{
                if (pywebchannel.objects.markerHandler) {{
                    pywebchannel.objects.markerHandler.on_marker_clicked("{loc.id}");
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
        for i, loc in enumerate(self.locations):
            if loc.id == marker_id:
                item = self.list_widget.item(i)
                self.list_widget.setCurrentItem(item)
                self.on_item_selected(item)

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
        js_code = f"""
        if (window.markerMap["{marker_id}"]) {{
            window.markerMap["{marker_id}"].setIcon(
                new L.Icon.Default
            );
        }}
        """
        self.map_page.runJavaScript(js_code)

    def add_location(self):
        logger.info(f"MapApp.add_location")
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            note = self.note_input.toPlainText()
            new_location = Location(lat=lat, lon=lon, note=note)
            self.locations.append(new_location)

            label = new_location.label()
            self.list_widget.addItem(f"{label}: {lat}, {lon}")
            self.update_map()
            # Get the last added item
            new_item = self.list_widget.item(self.list_widget.count() - 1)
            self.list_widget.setCurrentItem(new_item)  # Select it
            new_item.setSelected(True)

            # self.update_list()
            self.handle_marker_click(new_location.id)
            self.highlight_marker(new_location.id)
        except ValueError:
            print("Invalid latitude or longitude")

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
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addAction(save_as_nc_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        config_menu = menu_bar.addMenu("Settings")

        # Configuration action
        config_action = QAction("Configure OpenTripPlan", self)
        config_action.triggered.connect(self.open_config_dialog)
        config_menu.addAction(config_action)

    def open_config_dialog(self):
        """Open the configuration dialog"""
        dialog = ConfigDialog(self.settings, self)
        dialog.exec()

    def new(self):
        self.current_file = None
        self.locations = Journey()
        self.update_list()
        self.update_map()

    def load_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open JSON File",
            "",
            "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, "r") as file:
                    locations = json.load(file)
                    # Complete missing data
                    self.locations = Journey([Location.from_data(loc) for loc in locations])
                    self.current_file = file_name
                    self.update_list()
                    self.update_map()
            except Exception as e:
                QMessageBox.critical(self,
                                     "Error",
                                     f"Failed to load file: {str(e)}")

    def load_nc_file(self):
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
                logger.info(f"nc capabilities: {self.nc.capabilities}")
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
                logger.info(f"MapApp.load_nc_file got {selected_file}")
                node = self.nc.files.by_path(selected_file)
                json_bytes = self.nc.files.download(selected_file)
                # Convert bytes to a string
                json_str = json_bytes.decode('utf-8')

                # Parse JSON string into a Python object (dictionary in this case)
                locations = json.loads(json_str)

                # Complete missing data
                self.locations = Journey([Location.from_data(loc) for loc in locations])
                self.current_file = node  # keep nc_py_api FsNode instead of string
                self.update_list()
                self.update_map()

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
        elif type(self.current_file) == nc_py_api.FsNode:
            locations = [loc.to_dict() for loc in self.locations]
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
                self.nc.files.upload(self.current_file, data)
        else:
            self.write_to_file(self.current_file)

    def save_file_as(self):
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Save JSON File",
                                                   "",
                                                   "JSON Files (*.json)")
        if file_name:
            self.current_file = file_name
            self.write_to_file(file_name)

    def save_file_as_nc(self):
        logger.error(f"MapApp.save_file_as_nc NOT IMPLEMENTED")
        pass

    def write_to_file(self, file_name):
        try:
            locations = [loc.to_dict() for loc in self.locations]
            with open(file_name, "w") as file:
                json.dump(locations, file, indent=4)
        except Exception as e:
            QMessageBox.critical(self,
                                 "Error",
                                 f"Failed to save file: {str(e)}")

    def update_list(self):
        self.list_widget.clear()
        for item in self.locations:
            lat = str(item.lat)
            lat_val = QDoubleValidator(-90, 90, 3)
            lat_val.setNotation(QDoubleValidator.Notation.StandardNotation)
            lat_val.fixup(lat)

            lon_val = QDoubleValidator(-180, 180, 3)
            lon_val.setNotation(QDoubleValidator.Notation.StandardNotation)
            lon = str(item.lon)
            lon_val.fixup(lon)
            label = item.label()
            self.list_widget.addItem(f"{label}: {lat}, {lon}")

    def delete_item(self):
        pass
        selected_item = self.list_widget.currentItem()
        if selected_item:
            index = self.list_widget.row(selected_item)
            del self.locations[index]
            self.update_list()
            self.update_map()

    def on_item_selected(self, item):
        logger.info(f"MapApp.on_item_selected {item}")
        index = self.list_widget.row(item)
        loc = self.locations[index]
        self.lat_input.setText(str(loc.lat))
        self.lon_input.setText(str(loc.lon))
        self.note_input.setText(str(loc.note))
        for i in range(self.list_widget.count()):
            if i == index:
                self.highlight_marker(self.locations[i].id)
            else:
                self.downplay_marker(self.locations[i].id)
        js_code = f"moveMap({loc.lat}, {loc.lon});"
        self.map_page.runJavaScript(js_code)

    def close(self):
        QApplication.quit()

    def search_location(self):
        logger.info(f"MapApp.search_location {self.search_entry.text()}")
        query = self.search_entry.text().strip()
        if not query:
            self.search_popup.hide()
            return
        locations = self.geolocator.geocode(query, exactly_one=False)

        logger.info(f"Found: {locations}")

        # Show popup if results exist
        if locations:
            self.search_popup.show_popup(locations, self.search_entry)
        else:
            self.search_popup.hide()

    def handle_selected_location(self, location):
        """Handle the selected location"""
        logger.info(f"Selected: {location}")
        self.receiveData({"lat": location.latitude, "lon": location.longitude})

def main():
    # sys.argv.append("--disable-web-security")
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
