from PySide6.QtCore import QUrl, QFileInfo, QMimeData, QIODevice, QByteArray, QBuffer
from PySide6.QtGui import QTextCursor, QImageReader, QImage, QTextDocument
from PySide6.QtWidgets import QTextEdit
import os
import zipfile
import markdown
import tempfile
from PIL import Image
import io
import logging
import json

from typing import override

logger = logging.getLogger(__name__)


class NoteWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_counter = 1
        self.image_urls = []

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    @override
    def insertFromMimeData(self, source: QMimeData):
        logger.info(f"NoteWidget.insertFromMimeData")
        if source.hasImage():
            self.dropImage(QUrl(f"dropped_image_{self._image_counter}"), source.imageData())
            self._image_counter += 1
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
            if url.toString() not in self.image_urls:
                self.document().addResource(QTextDocument.ImageResource, url, image)
                self.image_urls.append(url.toString())
                if not url.toString() in self.toMarkdown():
                    self.textCursor().insertImage(url.toString())

    def dropTextFile(self, url: QUrl):
        file_path = url.toLocalFile()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                self.textCursor().insertText(file.read())

    def to_note(self):
        logger.info(f"NoteWidget.to_note")
        data = {}
        markdown_text = self.toMarkdown()
        data["markdown"] = markdown_text
        data["images"] = {}

        for image_url in self.image_urls:
            logger.info(f"NoteWidget.to_note {image_url}")
            image_data = self._extract_image_data(image_url)
            if image_data:
                logger.info(f"NoteWidget.to_note {image_url}: {len(image_data)}")
                data["images"][image_url] = image_data
        logger.info(f"NoteWidget.to_note: {json.dumps(data)[:500]}")
        return data

    def _extract_image_data(self, image_url):
        """
        Extract image data from a URL and return it as bytes.
        """
        # Extract the image resource from the document using the URL
        logger.info(f"NoteWidget._extract_image_data {image_url}")
        image = self.document().resource(QTextDocument.ImageResource, QUrl(image_url))
        if image is None:
            return None
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        image_data = ba.toBase64().toStdString()

        return image_data

    def from_note(self, data):
        if not "markdown" in data:
            QMessageBox.warning(this, "Invalid Note Data", "No markdown key in Json data")
            return
        logger.info(f"NoteWidget.from_note {data['markdown']}, {len(data['images'] if 'images' in data else '')}")
        self.clear()
        self.image_urls.clear()
        image_counter = 0
        markdown_content = data["markdown"]
        self.setMarkdown(markdown_content)

        if "images" in data:
            for image_url, image_data in data["images"].items():
                ba = QByteArray.fromBase64(QByteArray.fromStdString(image_data))
                image = QImage.fromData(ba, 'PNG')
                self.dropImage(QUrl(image_url), image)
                image_counter += 1
        self.document().setPageSize(self.viewport().size())  # Adjust page size
        self.document().adjustSize()  # Adjust document size
        self.ensureCursorVisible()  # Ensure proper scrolling

        logger.info(f"Content and {image_counter} images loaded successfully.")

# # Example usage
# def save_textedit_to_markdown(self: QTextEdit):
#     # Let the user select the output file location
#     file_dialog = QFileDialog()
#     file_name, _ = file_dialog.getSaveFileName(None, "Save Markdown with Images", "", "ZIP Files (*.zip)")
#
#     if file_name:
#         with open(file_name, 'wb') as zip_file_handler:
#             save_qtextedit_as_markdown(self, zip_file_handler)
