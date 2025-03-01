import logging
import os
import requests
import sys

from lxml import etree
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
    QPushButton, QDialog, QLineEdit, QFileDialog, QLabel, QListView,
    QMessageBox, QAbstractItemView, QWidget)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.root.setLevel(logging.DEBUG)

class NextcloudWebDAV:
    def __init__(self, base_url, username, password):
        uuid = self.get_user_uuid(base_url, username, password)
        self.uuid = uuid
        self.base_url = f"{base_url}/remote.php/dav/files/{uuid}"
        self.auth = HTTPBasicAuth(username, password)

    def get_user_uuid(self, nextcloud_url, username, password):
        api_url = f"{nextcloud_url}/ocs/v1.php/cloud/user"
        headers = {"OCS-APIRequest": "true"}

        response = requests.get(api_url, auth=(username, password), headers=headers)

        if response.status_code == 200:
            try:
                # Parse the XML response
                root = etree.fromstring(response.content)
                user_id = root.xpath('//ocs/data/id/text()')

                if user_id:
                    return user_id[0]
                else:
                    print("UUID not found in response.")
                    return None
            except Exception as e:
                print(f"Error parsing XML: {e}")
                return None
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None

    def parse_webdav_xml_file_list(self, xml_content):
        root = etree.fromstring(xml_content)
        namespace = {'d': 'DAV:'}
        entries = []

        for response in root.findall('d:response', namespace):
            href = response.find('d:href', namespace).text
            prop = response.find('d:propstat/d:prop', namespace)
            resource_type = prop.find('d:resourcetype', namespace)

            entry = {
                "type": "directory" if resource_type is not None and resource_type.find('d:collection', namespace) is not None else "file",
                "path": "/".join(href.split('/')[5:]),
                "hidden": href.split('/')[-1].startswith('.')
            }
            entries.append(entry)

        return entries

    def list_files(self, path=""):
        url = f"{self.base_url}/{path}"
        response = requests.request("PROPFIND", url, auth=self.auth)
        if response.status_code == 207:  # 207 means directory exists (WebDAV specific)
            QMessageBox.critical(
                None,
                "Error",
                f"response: {response.text}")
            content = self.parse_webdav_xml_file_list(response.text)
            return content
        elif response.status_code == 404:
            QMessageBox.critical(
                None,
                "Error",
                f"Directory '{path}' does not exist.")
            return []
        else:
            QMessageBox.critical(
                None,
                "Error",
                f"Unexpected response: {response.status_code} - {response.text}")
            return []
        return []

    def download_file(self, remote_path, local_path):
        url = f"{self.base_url}/{remote_path}"
        response = requests.get(url, auth=self.auth, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

    def upload_file(self, local_path, remote_path):
        logger.info(f"upload_file {local_path}, {remote_path}")
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
            if file["type"] == "directory" and not file["hidden"]:
                item = QStandardItem(f"[{file['path']}]")
                self.list_model.appendRow(item)
        for file in files:
            if file["type"] == "file" and not file["hidden"]:
                item = QStandardItem(file["path"])
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
            password="yyy"
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
                local_path = os.path.join(os.getcwd(),
                                          os.path.basename(selected_file))
                self.nextcloud.download_file(selected_file, local_path)
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
