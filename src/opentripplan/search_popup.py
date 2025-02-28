from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    )

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
        self.clear()
        if not locations:
            self.hide()
            return

        # Populate list with location items
        for loc in locations:
            item = QListWidgetItem(str(loc))
            item.setData(Qt.UserRole, loc)  # Store Location object
            self.addItem(item)

        # Adjust size dynamically
        self.setFixedSize(search_entry.width(), min(200, self.sizeHintForRow(0) * len(locations)))

        # Position just below search_entry
        rect: QRect = search_entry.geometry()
        global_pos = search_entry.mapToGlobal(rect.bottomLeft())
        self.move(global_pos)

        self.show()

    def select_location(self, item):
        """Handle selection and hide popup"""
        location = item.data(Qt.UserRole)  # Retrieve the stored Location object
        if location and self.parent():
            self.parent().handle_selected_location(location)
        self.hide()  # Hide popup after selection

