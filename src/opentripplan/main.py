import folium
import io
import json
import logging
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSlot, QObject, QVariant, pyqtSignal
from PyQt6.QtGui import QAction, QDoubleValidator, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
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
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

from branca.element import Element
from folium.elements import *
from pathlib import Path

from .location import Location

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.root.setLevel(logging.DEBUG)


class MarkerHandler(QObject):
    """ Exposes a slot to receive marker click events from JavaScript. """
    markerClicked = pyqtSignal(str)  # Signal to send marker ID when clicked

    @pyqtSlot(str)
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
        self.channel = QWebChannel()
        self.marker_handler = MarkerHandler()
        self.channel.registerObject("markerHandler", self.marker_handler)
        self.channel.registerObject("pyObj", self)

        # Connect markerClicked signal to a Python slot
        self.marker_handler.markerClicked.connect(self.handle_marker_click)

        self.setWindowTitle("Open Trip Planner")
        self.setGeometry(100, 100, 800, 600)

        self.current_file = None
        self.locations = []

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

    @pyqtSlot(QVariant)
    def receiveData(self, data):
        if isinstance(data, QVariant):
            data = data.toVariant()  # Convert QVariant to Python object
        logger.debug(f"MapApp.receiveData Received from JS: {data}")
        data["note"] = ""
        try:
            self.lat_input.setText(str(data["lat"]))
            self.lon_input.setText(str(data["lon"]))
            self.note_input.setText("")
            self.add_location()
        except json.JSONDecodeError as e:
            pass

    @pyqtSlot()
    def note_changed(self):
        # logger.info(f"MapApp.text_changed")
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
        logger.info(f"Python received marker click event for: {marker_id}")
        for i, loc in enumerate(self.locations):
            if loc.id == marker_id:
                item = self.list_widget.item(i)
                self.list_widget.setCurrentItem(item)
                self.on_item_selected(item)

    def highlight_marker(self, marker_id):
        """ Change marker color dynamically without modifying tooltip """
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
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            note = self.note_input.toPlainText()
            new_location = Location(lat=lat, lon=lon, note=note)
            self.locations.append(new_location)
            self.update_list()
            self.update_map()
            self.highlight_marker(new_location.id)
            self.handle_marker_click(new_location.id)
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

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_file)

        save_as_action = QAction("Save As…", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self.save_file_as)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(load_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

    def new(self):
        self.current_file = None
        self.locations = []
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
                    self.locations = [Location.from_data(loc) for loc in locations]
                    self.current_file = file_name
                    self.update_list()
                    self.update_map()
            except Exception as e:
                QMessageBox.critical(self,
                                     "Error",
                                     f"Failed to load file: {str(e)}")

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
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
        for i in range(len(self.list_widget)):
            if i == index:
                self.highlight_marker(self.locations[i].id)
            else:
                self.downplay_marker(self.locations[i].id)
        js_code = f"moveMap({loc.lat}, {loc.lon});"
        self.map_page.runJavaScript(js_code)

    def close(self):
        QApplication.quit()


def main():
    # sys.argv.append("--disable-web-security")
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
