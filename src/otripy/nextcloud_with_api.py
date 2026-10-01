import json
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

try:
    from .journey import Journey
    from .location import Location
except ImportError:
    from journey import Journey
    from location import Location

logger = logging.getLogger(__name__)


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
