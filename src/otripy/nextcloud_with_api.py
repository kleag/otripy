import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout,
    QDialog, QDialogButtonBox, QLineEdit, QListView,
    QAbstractItemView)
from PySide6.QtGui import QStandardItemModel, QStandardItem

logger = logging.getLogger(__name__)

# Kind of each entry of the list, stored in its item
ENTRY_KIND = Qt.UserRole
PARENT, DIRECTORY, FILE = "parent", "directory", "file"


class NextcloudFilePicker(QDialog):
    """Browse Nextcloud folders to pick a file to open or, with save, a file name to save to."""

    def __init__(self, nextcloud, parent=None, save=False):
        super().__init__(parent)
        self.save = save
        self.setWindowTitle("Save to Nextcloud" if save else "Select File from Nextcloud")
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

        if self.save:
            self.name_line_edit = QLineEdit()
            self.name_line_edit.setPlaceholderText("File name, e.g. trip.json")
            self.name_line_edit.returnPressed.connect(self.accept_name)
            layout.addWidget(self.name_line_edit)
            buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept_name)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

        self.setLayout(layout)
        self.refresh_files()  # Initially load the root directory

    def add_entry(self, text, kind, name=None):
        item = QStandardItem(text)
        item.setData(kind, ENTRY_KIND)
        item.setData(name if name is not None else text, Qt.UserRole + 1)
        self.list_model.appendRow(item)

    def refresh_files(self):
        directory = self.path_line_edit.text().strip()
        files = self.nc.files.listdir(directory)
        self.list_model.clear()  # Clear previous entries
        if directory:
            self.add_entry("[..]", PARENT)
        for file in files:
            if file.is_dir:
                self.add_entry(f"[{file.name}]", DIRECTORY, file.name)
        for file in files:
            if not file.is_dir:
                self.add_entry(file.name, FILE)

    def on_file_selected(self, index):
        item = self.list_model.itemFromIndex(index)
        kind, name = item.data(ENTRY_KIND), item.data(Qt.UserRole + 1)
        logger.info(f"on_file_selected {kind} {name}")
        if kind == PARENT:
            directory = self.path_line_edit.text().strip().rstrip("/")
            self.path_line_edit.setText("/".join(directory.split("/")[:-1]))
            self.refresh_files()
        elif kind == DIRECTORY:
            self.path_line_edit.setText(self.path_line_edit.text().strip() + "/" + name)
            self.refresh_files()
        elif self.save:
            self.name_line_edit.setText(name)  # save over this file, after confirmation
        else:
            self.selected_file = name
            self.accept()

    def accept_name(self):
        """Save mode: accept the typed file name, adding the .json extension if missing."""
        name = self.name_line_edit.text().strip().strip("/")
        if not name:
            return
        if not name.lower().endswith(".json"):
            name += ".json"
        self.selected_file = name
        self.accept()

    def get_selected_file(self):
        return self.path_line_edit.text().strip() + "/" + self.selected_file
