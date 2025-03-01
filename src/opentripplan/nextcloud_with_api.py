import logging
import nc_py_api
import os
import sys

from lxml import etree
from PySide6.QtCore import QSettings, QUrl, QObject, Signal, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
    QPushButton, QDialog, QLineEdit, QFileDialog, QLabel, QListView,
    QMessageBox, QAbstractItemView, QWidget)
from PySide6.QtGui import QStandardItemModel, QStandardItem

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.root.setLevel(logging.DEBUG)


class NextcloudFilePicker(QDialog):
    def __init__(self, nextcloud, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select File from Nextcloud")
        self.nc = nextcloud
        self.selected_file = None
        self.current_dir = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.path_line_edit = QLineEdit()
        self.path_line_edit.setReadOnly(True)
        self.path_line_edit.setPlaceholderText(
            "Enter directory on Nextcloud (e.g., /folder1/)")
        layout.addWidget(self.path_line_edit)

        self.list_view = QListView()
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)
        self.list_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.clicked.connect(self.on_file_selected)
        layout.addWidget(self.list_view)

        self.setLayout(layout)
        self.refresh_files()  # Initially load the root directory

    def refresh_files(self):
        directory = self.path_line_edit.text().strip()
        files = self.nc.files.listdir(directory)
        self.list_model.clear()  # Clear previous entries
        if directory:
            item = QStandardItem("[..]")
            self.list_model.appendRow(item)
        for file in files:
            if file.is_dir:  # and not file["hidden"]:
                item = QStandardItem(f"[{file.name}]")
                self.list_model.appendRow(item)
        for file in files:
            if not file.is_dir:  # and not file["hidden"]:
                item = QStandardItem(file.name)
                self.list_model.appendRow(item)

    def on_file_selected(self, index):
        self.selected_file = self.list_model.itemFromIndex(index).text()
        logger.info(f"on_file_selected {index}, {self.selected_file}")
        if self.selected_file == "[..]":
            directory = self.path_line_edit.text().strip()
            if directory[-1] == "/":
                directory = directory[:-1]
            directory = "/".join(directory.split("/")[:-1])
            logger.info(f"on_file_selected .. directory: {directory}")
            self.path_line_edit.setText(directory)
            self.refresh_files()
        elif self.selected_file[0] == "[" and self.selected_file[-1] == "]":
            directory = self.path_line_edit.text().strip() + "/" + self.selected_file[1:-1]
            self.path_line_edit.setText(directory)
            self.refresh_files()
        else:
            self.accept()

    def get_selected_file(self):
        return self.path_line_edit.text().strip() + "/" + self.selected_file

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Kleag", "OpenTripPlan")

        self.setWindowTitle("Nextcloud File Operations")
        self.setGeometry(100, 100, 400, 200)

        # Initialize Nextcloud connection
        base_url = self.settings.value("nextcloud/url", "")
        username = self.settings.value("nextcloud/username", "")
        password = self.settings.value("nextcloud/password", "")
        self.nc = nc_py_api.Nextcloud(nextcloud_url=base_url, nc_auth_user=username, nc_auth_pass=password)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.info_label = QLabel("Choose to open or save a file")
        layout.addWidget(self.info_label)

        self.open_button = QPushButton("Open File from Nextcloud")
        self.open_button.clicked.connect(self.open_file_from_nextcloud)
        layout.addWidget(self.open_button)

        self.save_button = QPushButton("Save File to Nextcloud")
        self.save_button.clicked.connect(self.save_file_to_nextcloud)
        layout.addWidget(self.save_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_file_from_nextcloud(self):
        # Open a custom dialog to select a file from Nextcloud
        file_picker = NextcloudFilePicker(self.nc, self)
        if file_picker.exec() == QDialog.DialogCode.Accepted:
            selected_file = file_picker.get_selected_file()
            if selected_file:
                local_path = os.path.join(os.getcwd(),
                                          os.path.basename(selected_file))
                with open(local_path, "wb") as file:
                    file.write(self.nc.files.download(selected_file))
                self.info_label.setText(
                    f"Downloaded {selected_file} to local path {local_path}")

    def save_file_to_nextcloud(self):
        # Show file dialog to select file to save
        local_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Json Files (*.json);;All Files (*)",
            options=QFileDialog.DontConfirmOverwrite)
        if local_file:
            logger.info(f"save_file_to_nextcloud: {local_file}")
            # If file selected, upload to Nextcloud
            remote_path = os.path.basename(local_file)
            try:
                with open(local_file, "rb") as file:
                    self.nc.files.upload_stream(remote_path, file)
                self.info_label.setText(f"Uploaded {local_file} to Nextcloud")
            except nc_py_api.NextcloudException as e:
                self.info_label.setText(f"Error uploading: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
