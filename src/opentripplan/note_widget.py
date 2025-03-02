from PySide6.QtCore import QUrl, QFileInfo, QMimeData, QIODevice
from PySide6.QtGui import QTextCursor, QImageReader, QImage, QTextDocument
from PySide6.QtWidgets import QTextEdit
import os

class NoteWidget(QTextEdit):
    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData):
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
            self.document().addResource(QTextDocument.ImageResource, url, image)
            self.textCursor().insertImage(url.toString())

    def dropTextFile(self, url: QUrl):
        file_path = url.toLocalFile()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                self.textCursor().insertText(file.read())

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_counter = 1
