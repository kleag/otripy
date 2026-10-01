from PySide6.QtCore import QUrl, QFileInfo, QMimeData, QIODevice, QByteArray, QBuffer
from PySide6.QtGui import QImage, QImageReader, QPixmap, QTextDocument
from PySide6.QtWidgets import QMessageBox, QTextEdit
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


class NoteWidget(QTextEdit):
    """Rich text note editor. Images are document resources, saved as base64 PNG in the note."""

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
        return {"markdown": markdown_text, "images": images}

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
            QMessageBox.warning(self, "Invalid Note Data", "No markdown key in Json data")
            return
        self.clear()
        self.setMarkdown(data["markdown"])
        # setMarkdown clears the document resources: add the images after it, then relayout
        for name, image_data in data.get("images", {}).items():
            self._add_image(name, image_data)
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
