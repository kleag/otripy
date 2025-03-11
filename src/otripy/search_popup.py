import logging
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    )

logger = logging.getLogger(__name__)


class SearchPopup(QListWidget):
    """Popup list that appears under the search bar"""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setFocusPolicy(Qt.NoFocus)  # Prevent it from stealing focus
        self.setSelectionMode(QListWidget.SingleSelection)
        self.itemClicked.connect(self.select_location)

    def show_popup(self, locations, search_entry):
        """Position the popup under the search entry and populate it"""
        # logger.info(f"SearchPopup.show_popup {len(locations if locations else '')}, {search_entry}")
        self.clear()

        no_location = False
        # Populate list with location items
        if not locations:
            no_location = True
            locations = ["<No Result>"]
        for loc in locations:
            item = QListWidgetItem(str(loc))
            item.setData(Qt.UserRole, loc)  # Store Location object
            self.addItem(item)

        # Adjust size dynamically
        height = self.sizeHintForRow(0) * len(locations)
        self.setFixedSize(search_entry.width(), min(200, height))

        # Position just below search_entry
        rect: QRect = search_entry.geometry()
        global_pos = search_entry.mapToGlobal(rect.bottomLeft())
        self.move(global_pos)

        # if no_location:
        #     logger.debug(f"SearchPopup.show_popup no location. {self.size()}, {global_pos}")
        #     self.show()
        #     time.sleep(5)
        #     self.clear()
        #     self.hide()
        #     return
        # else:
        #     self.show()
        self.show()

    def select_location(self, item):
        """Handle selection and hide popup"""
        location = item.data(Qt.UserRole)  # Retrieve the stored Location object
        # logger.info(f"SearchPopup.select_location '{str(location)}'")
        if str(location) == "<No Result>":
            self.clear()
        elif location and self.parent():
            self.parent().handle_selected_location(location)
        self.hide()  # Hide popup after selection


    def keyPressEvent(self, event):
        """Close popup on Escape key"""
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
