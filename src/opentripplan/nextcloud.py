import sys
import os
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QDialog, QLineEdit, QHBoxLayout, QFileDialog, QLabel, QListView, QAbstractItemView, QWidget
from PyQt6.QtGui import QIcon, QStandardItemModel, QStandardItem
from requests.auth import HTTPBasicAuth
import requests

class NextcloudWebDAV:
    def __init__(self, base_url, username, password):
        self.base_url = f"{base_url}/remote.php/dav/files/{username}"
        self.auth = HTTPBasicAuth(username, password)

    def list_files(self, path=""):
        url = f"{self.base_url}/{path}"
        response = requests.request("PROPFIND", url, auth=self.auth)
        return response.text  # Process XML response

    def download_file(self, remote_path, local_path):
        url = f"{self.base_url}/{remote_path}"
        response = requests.get(url, auth=self.auth, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

    def upload_file(self, local_path, remote_path):
        url = f"{self.base_url}/{remote_path}"
        with open(local_path, "rb") as file:
            response = requests.put(url, data=file, auth=self.auth)
        return response.status_code



class NextcloudFilePicker(QDialog):
    def __init__(self, nextcloud, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select File from Nextcloud")
        self.nextcloud = nextcloud
        self.selected_file = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.path_line_edit = QLineEdit()
        self.path_line_edit.setPlaceholderText("Enter directory on Nextcloud (e.g., /folder1/)")
        layout.addWidget(self.path_line_edit)

        self.list_view = QListView()
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.clicked.connect(self.on_file_selected)
        layout.addWidget(self.list_view)

        self.refresh_button = QPushButton("Refresh Files")
        self.refresh_button.clicked.connect(self.refresh_files)
        layout.addWidget(self.refresh_button)

        self.select_button = QPushButton("Select File")
        self.select_button.clicked.connect(self.accept)
        layout.addWidget(self.select_button)

        self.setLayout(layout)
        self.refresh_files()  # Initially load the root directory

    def refresh_files(self):
        directory = self.path_line_edit.text().strip()
        files = self.nextcloud.list_files(directory)

        self.list_model.clear()  # Clear previous entries
        for file in files:
            item = QStandardItem(file)
            self.list_model.appendRow(item)

    def on_file_selected(self, index):
        self.selected_file = self.list_model.itemFromIndex(index).text()

    def get_selected_file(self):
        return self.selected_file


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nextcloud File Operations")
        self.setGeometry(100, 100, 400, 200)

        # Initialize Nextcloud connection
        self.nextcloud = NextcloudWebDAV(
            base_url="https://myrga.nsupdate.info",
            username="xxx",
            password="xxx"
        )

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
        file_picker = NextcloudFilePicker(self.nextcloud, self)
        if file_picker.exec() == QDialog.DialogCode.Accepted:
            selected_file = file_picker.get_selected_file()
            if selected_file:
                local_path = os.path.join(os.getcwd(), os.path.basename(selected_file))
                self.nextcloud.download_file(selected_file, local_path)
                self.info_label.setText(f"Downloaded {selected_file} to local path {local_path}")

    def save_file_to_nextcloud(self):
        # Show file dialog to select file to save
        local_file, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if local_file:
            # If file selected, upload to Nextcloud
            remote_path = os.path.basename(local_file)
            upload_status = self.nextcloud.upload_file(local_file, remote_path)
            if upload_status == 201:
                self.info_label.setText(f"Uploaded {local_file} to Nextcloud")
            else:
                self.info_label.setText(f"Error uploading {local_file}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
