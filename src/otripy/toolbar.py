"""
Otripy toolbar.
This code has been borrowed from Notolog Editor,
An open-source Markdown editor built with Python, released under the MIT
License which authorizes to reuse and to relicense the code.

File Details:
- Purpose: Provides app toolbar UI.
- Functionality: Displays the app's toolbar icons and search form. Supports context menu for adjusting icon elements.

Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app
PyPI: https://pypi.org/project/notolog

Author: Vadim Bakhrenkov
Copyright: 2024-2025 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""
import logging

from importlib import resources
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap, QPainter, QFont
from PySide6.QtWidgets import QToolBar, QWidget, QMenu, QToolButton, QSizePolicy


if TYPE_CHECKING:
    from typing import Union  # noqa
    from ..notolog_editor import NotologEditor  # noqa

logger = logging.getLogger(__name__)

RESOURCE_DIR = "resources/icons"

class ToolBar(QToolBar):
    # Main window toolbar class

    BASE_ICON_SIZE = 64  # type: int

    def __init__(self, parent, actions=None, refresh=None):
        """
        Args:
            parent (optional): Parent object
            actions (List[Dict[str, Any]], optional): The map with the toolbar's icons
            refresh (Callable[[int, int], int], optional): A lambda function that refreshes a toolbar
        """
        super(ToolBar, self).__init__(parent)

        self.parent = parent  # type: NotologEditor

        if self.parent and hasattr(self.parent, 'font'):
            # Apply the font from the main window to this dialog
            self.setFont(self.parent.font())


        self.actions = actions if actions else {}
        self.refresh = refresh

        self.settings = QSettings("Kleag", "Otripy")

        self.toolbar_save_button = None  # type: Union[QToolButton, None]
        self.toolbar_edit_button = None  # type: Union[QToolButton, None]

        self.setMovable(False)

        self.init_ui()

    def init_ui(self):
        """
        Build the toolbar's UI components by dynamically creating toolbar
        icons and adding a search form based on defined actions and settings.
        """

        # Adjust layout margins for proper spacing
        self.setContentsMargins(0, 1, 5, 1)

        # Calculate and set the icon size based on the height of the search
        # input.
        # Set the fixed size for the search form first, or use a hinted size.
        icon_width = icon_height = int(20 * 0.85)
        self.setIconSize(QSize(icon_width, icon_height))

        # Set a minimum height for the toolbar
        self.setMinimumHeight(int(20 * 1.5))

        # Initialize the previous icon type to manage delimiters
        prev_type = None

        # Iterate over action configurations.
        for icon in self.actions:
            if icon['type'] == 'action':
                # Add the toolbar icon if all conditions are met.
                self.append_toolbar_icon(icon)
            # Add a separator unless the last added item was also a delimiter.
            elif icon['type'] == 'delimiter' and prev_type != 'delimiter':
                self.addSeparator()
            # Update previous icon type to manage delimiters correctly.
            prev_type = icon['type']

        # Add a spacer to separate icons from the search form.
        central_spacer = QWidget(self)
        central_spacer.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.addWidget(central_spacer)

    def append_toolbar_icon(self, conf):
        """
        Helper to create, add to the toolbar and return button with an icon.
        """
        # Use a themed icon with a fallback to a system icon
        system_icon = conf['system_icon'] if 'system_icon' in conf else None
        if resources.files("otripy.resources.icons"):  # Check if the module is available
            # Use importlib.resources to list all SVG files in the package resources
            if 'theme_icon' in conf:
                icon_resource = resources.files("otripy.resources.icons") / conf['theme_icon']
                with resources.as_file(icon_resource) as icon_path:
                    theme_icon = str(icon_path.resolve())
            else:
                theme_icon = None
        else:
            # Fallback to local directory if not installed
            theme_icon = f"{RESOURCE_DIR}/{conf['theme_icon']}" if 'theme_icon' in conf else None
        # logger.info(f"append_toolbar_icon {conf}. theme_icon: {theme_icon}")
        text_icon = conf['text_icon'] if 'text_icon' in conf else None
        width = height = max(self.BASE_ICON_SIZE, 11)
        # logger.info(f"append_toolbar_icon {system_icon}, {theme_icon}, {text_icon}")
        icon = (QIcon(theme_icon) if theme_icon
                else (QIcon.fromTheme(system_icon) if system_icon
                      else self.create_text_icon(text_icon, 20)))

        # Button's action
        label = conf['label'] if 'label' in conf else ''
        icon_action = QAction(icon, label, self)
        action = conf['action'] if 'action' in conf else None  # Action triggered on click
        if action is not None:
            icon_action.triggered.connect(action)

        # Toolbar button itself
        icon_button = QToolButton(self)
        if 'name' in conf:
            icon_button.setObjectName(conf['name'])
        icon_button.setToolTip(label)
        icon_button.setDefaultAction(icon_action)
        # icon_action.setChecked(True)
        if 'accessible_name' in conf:
            icon_button.setAccessibleName(conf['accessible_name'])

        # Add the button to the toolbar
        self.addWidget(icon_button)

        # Add an internal variable to access the icon later, e.g., for state toggling
        if 'var_name' in conf:
            if hasattr(self, conf['var_name']):
                logger.debug('Variable "%s" is already set! Re-writing it...' % conf['var_name'])
            setattr(self, conf['var_name'], icon_button)  # type: QToolButton
        # If the icon has a switched-off check, handle it here
        if ('switched_off_check' in conf
                and callable(conf['switched_off_check'])
                and conf['switched_off_check']()):
            # Switch the icon off
            icon_button.setDisabled(True)

    def contextMenuEvent(self, event):
        """
        Render context menu event upon the toolbar right mouse click
        """
        current_action = self.actionAt(event.pos())
        if current_action is None:
            return

        if self.actions is None:
            return

        context_menu = QMenu(self)

        _weights = 0
        for index, label in enumerate(self.actions, 1):
            if 'type' not in label or label['type'] != 'action':
                context_menu.addSeparator()
                continue

            # Get settings weight of the item
            settings_weight = pow(2, label['weight'])

            if _weights & settings_weight:
                # The item is already added or the active state item that shouldn't be duplicated
                continue

            button = QAction(label['label'], self)
            button.setFont(self.font())

            # Method def instead of lambda
            def slot(checked, i=label['weight']):
                self.toolbar_menu_item(checked, i)

            # Check button.toggled.connect()
            button.triggered[bool].connect(slot)
            button.setCheckable(True)
            # Check the item is in the settings weights
            button.setChecked(self.settings.toolbar_icons & settings_weight)

            context_menu.addAction(button)

            # Collect items already added to the context menu
            _weights |= settings_weight

        # PoC remove element from the toolbar
        # delete_action  = menu.addAction("Hide")

        context_menu.exec(event.globalPos())

        # PoC Remove element from the toolbar
        # if action == delete_action:
        #    self.removeAction(current_action)

    def toolbar_menu_item(self, checked: bool, index: int) -> None:
        """
        Draw context menu item with a checkbox

        Args:
            checked (bool): Checked or not
            index (int): Index in a toolbar menu mapping
        """
        pi = pow(2, index)
        # logger.debug('checked:{} index:{} pi:{}' . format(checked, index, pi))
        if checked:
            self.settings.toolbar_icons |= pi
        else:
            self.settings.toolbar_icons ^= pi
        # Re-draw toolbar with a callback
        if callable(self.refresh):
            self.refresh()

    # PoC Remove element from the toolbar
    # def removeAction(self, action):
    #    """
    #    Override removeAction() method upon QWidgetAction
    #
    #    Args:
    #        action (QAction):
    #    """
    #    super(ToolBar, self).removeAction(action)
    #
    #    logger.debug('Remove element action "%s"' % action)

    def create_text_icon(self, text="H1", size=20):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Transparent background

        painter = QPainter(pixmap)
        font = QFont("Sans Serif", size // 2)  # Adjust font size
        painter.setFont(font)
        painter.setPen(Qt.black)  # Set text color
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()

        return QIcon(pixmap)
