from PySide6.QtCore import QT_TRANSLATE_NOOP, QUrl, QFileInfo, QMimeData, QIODevice, QByteArray, QBuffer, Qt
from PySide6.QtGui import QDesktopServices, QImage, QImageReader, QPixmap, QTextCursor, QTextDocument, QTextFormat
from PySide6.QtWidgets import QMenu, QMessageBox, QTextEdit, QToolTip
import os
import logging
import json
import re
import uuid

from typing_extensions import override

logger = logging.getLogger(__name__)


# Image references in the markdown written by QTextDocument.toMarkdown: ![alt](name)
IMAGE_REF = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
# Clipboard format carrying the data of the images in a cut or copied selection
IMAGES_MIME_TYPE = "application/x-otripy-images"
# Display widths offered for images in notes (issue #20); None is the original size
IMAGE_SIZES = ((QT_TRANSLATE_NOOP("NoteWidget", "Small"), 160), (QT_TRANSLATE_NOOP("NoteWidget", "Medium"), 320),
               (QT_TRANSLATE_NOOP("NoteWidget", "Large"), 640), (QT_TRANSLATE_NOOP("NoteWidget", "Original Size"), None))
# Web addresses typed as plain text, which are not links in the document
BARE_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"]+")


class NoteWidget(QTextEdit):
    """Rich text note editor. Images are document resources, saved as base64 PNG in the note.

    Ctrl+click opens links, and web addresses typed as plain text, in the browser.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewport().setMouseTracking(True)  # to show when Ctrl+click would open a link

    def link_at(self, pos) -> str | None:
        """Return the URL of the link, or of the web address, at a viewport position."""
        # Links, including the web addresses Qt turns into links when loading markdown
        anchor = self.anchorAt(pos)
        if anchor:
            return anchor
        # Web addresses typed since the note was loaded are still plain text
        cursor = self.cursorForPosition(pos)
        column = cursor.positionInBlock()
        for match in BARE_URL.finditer(cursor.block().text()):
            if match.start() <= column < match.end():
                url = match.group().rstrip(".,;:!?)]}'")
                # Like the links Qt makes from such addresses when loading a note
                return url if "://" in url else "http://" + url
        return None

    @override
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        link = self.link_at(event.position().toPoint())
        if link and event.modifiers() & Qt.ControlModifier:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
        if link:
            QToolTip.showText(event.globalPosition().toPoint(), self.tr("Ctrl+click to open {url}").format(url=link), self)

    @override
    def mouseReleaseEvent(self, event):
        link = self.link_at(event.position().toPoint())
        if (link and event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier
                and not self.textCursor().hasSelection()):
            QDesktopServices.openUrl(QUrl(link))
            return
        super().mouseReleaseEvent(event)

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    @override
    def createMimeDataFromSelection(self) -> QMimeData:
        mime = super().createMimeDataFromSelection()
        # The selection only references its images: carry their data so they
        # survive being pasted into another note.
        markdown = self.textCursor().selection().toMarkdown()
        images = {name: data for name in IMAGE_REF.findall(markdown)
                  if (data := self._image_data(name))}
        if not images:
            return mime
        # Qt's own mime data object lists a fixed set of formats: copy them to add ours
        result = QMimeData()
        for mime_format in mime.formats():
            result.setData(mime_format, mime.data(mime_format))
        result.setData(IMAGES_MIME_TYPE, QByteArray(json.dumps(images).encode()))
        return result

    @override
    def insertFromMimeData(self, source: QMimeData):
        logger.info("NoteWidget.insertFromMimeData")
        if source.hasFormat(IMAGES_MIME_TYPE):
            images = json.loads(bytes(source.data(IMAGES_MIME_TYPE).data()).decode())
            for name, data in images.items():
                self._add_image(name, data)
            super().insertFromMimeData(source)
        elif source.hasImage():
            self.dropImage(QUrl(f"image_{uuid.uuid4().hex}"), source.imageData())
        elif source.hasUrls():
            for url in source.urls():
                info = QFileInfo(url.toLocalFile())
                if QImageReader.supportedImageFormats().contains(info.suffix().lower().encode()):
                    self.dropImage(url, QImage(info.filePath()))
                else:
                    self.dropTextFile(url)
        else:
            super().insertFromMimeData(source)

    def dropImage(self, url: QUrl, image: QImage):
        if not image.isNull():
            logger.info(f"NoteWidget.dropImage {url}")
            self.document().addResource(QTextDocument.ImageResource, url, image)
            self.textCursor().insertImage(url.toString())

    def dropTextFile(self, url: QUrl):
        file_path = url.toLocalFile()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                self.textCursor().insertText(file.read())

    def to_note(self):
        """Return the note as markdown plus the images it references, as base64 PNG."""
        markdown_text = self.toMarkdown()
        images = {name: data for name in IMAGE_REF.findall(markdown_text)
                  if (data := self._image_data(name))}
        note = {"markdown": markdown_text, "images": images}
        # Markdown keeps no image size: save the widths set in the editor separately
        widths = {name: width for name, width in self.image_widths().items() if name in images}
        if widths:
            note["image_widths"] = widths
        return note

    def _image_fragments(self):
        """Yield the document fragments that are images."""
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    yield fragment
                it += 1
            block = block.next()

    def image_widths(self) -> dict:
        """Return the display width of the resized images, by image name."""
        widths = {}
        for fragment in self._image_fragments():
            image_format = fragment.charFormat().toImageFormat()
            if image_format.hasProperty(QTextFormat.Property.ImageWidth):
                widths[image_format.name()] = round(image_format.width())
        return widths

    def image_cursor_at(self, pos):
        """Return a cursor selecting the image at a viewport position, or None."""
        position = self.cursorForPosition(pos).position()
        for end in (position, position + 1):  # the image is just before or after the position
            if 1 <= end < self.document().characterCount():
                cursor = QTextCursor(self.document())
                cursor.setPosition(end - 1)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                if cursor.charFormat().isImageFormat():
                    return cursor
        return None

    def set_image_width(self, cursor, width):
        """Set the display width of the image selected by cursor; None restores its original size."""
        image_format = cursor.charFormat().toImageFormat()
        image_format.clearProperty(QTextFormat.Property.ImageHeight)  # keep the aspect ratio
        if width:
            image_format.setWidth(width)
        else:
            image_format.clearProperty(QTextFormat.Property.ImageWidth)
        cursor.setCharFormat(image_format)

    def build_context_menu(self, pos):
        """Return the context menu for a viewport position: the standard one, plus image sizes on images."""
        menu = self.createStandardContextMenu(pos)
        image_cursor = self.image_cursor_at(pos)
        if image_cursor is not None:
            menu.addSeparator()
            # Parented to the menu: a submenu owned by Python would be deleted on return
            size_menu = QMenu(self.tr("Image Size"), menu)
            menu.addMenu(size_menu)
            for label, width in IMAGE_SIZES:
                action = size_menu.addAction(self.tr(label))
                action.triggered.connect(lambda checked=False, width=width: self.set_image_width(image_cursor, width))
        return menu

    @override
    def contextMenuEvent(self, event):
        menu = self.build_context_menu(event.pos())
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _image_data(self, name):
        """Return the image resource with this name as base64 PNG, or None."""
        image = self.document().resource(QTextDocument.ImageResource, QUrl(name))
        if isinstance(image, QPixmap):
            image = image.toImage()
        if not isinstance(image, QImage) or image.isNull():
            return None
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        return ba.toBase64().toStdString()

    def _add_image(self, name, data):
        ba = QByteArray.fromBase64(QByteArray.fromStdString(data))
        self.document().addResource(QTextDocument.ImageResource, QUrl(name), QImage.fromData(ba, 'PNG'))

    def from_note(self, data):
        if "markdown" not in data:
            QMessageBox.warning(self, self.tr("Invalid Note Data"), self.tr("No markdown key in Json data"))
            return
        self.clear()
        self.setMarkdown(data["markdown"])
        # setMarkdown clears the document resources: add the images after it, then relayout
        for name, image_data in data.get("images", {}).items():
            self._add_image(name, image_data)
        widths = data.get("image_widths", {})
        if widths:
            for fragment in list(self._image_fragments()):
                name = fragment.charFormat().toImageFormat().name()
                if name in widths:
                    cursor = QTextCursor(self.document())
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                    self.set_image_width(cursor, widths[name])
        document = self.document()
        document.markContentsDirty(0, document.characterCount())
        document.setPageSize(self.viewport().size())  # Adjust page size
        document.adjustSize()  # Adjust document size
        self.ensureCursorVisible()  # Ensure proper scrolling


# # Example usage
# def save_textedit_to_markdown(self: QTextEdit):
#     # Let the user select the output file location
#     file_dialog = QFileDialog()
#     file_name, _ = file_dialog.getSaveFileName(None, "Save Markdown with Images", "", "ZIP Files (*.zip)")
#
#     if file_name:
#         with open(file_name, 'wb') as zip_file_handler:
#             save_qtextedit_as_markdown(self, zip_file_handler)
