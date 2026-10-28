from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QWidget


class VideoWidget(QWidget):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.image = None
        self.placeholder = placeholder
        self.setMinimumSize(320, 180)

    def set_frame(self, bgr):
        h, w = bgr.shape[:2]
        # Own the image; the worker will replace its ndarray on the next frame.
        self.image = QImage(bgr.data, w, h, bgr.strides[0], QImage.Format.Format_BGR888).copy()
        self.update()

    def clear(self):
        self.image = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#080b10"))
        if self.image is not None:
            size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            rect = QRect((self.width()-size.width())//2, (self.height()-size.height())//2,
                         size.width(), size.height())
            painter.drawImage(rect, self.image)
        elif self.placeholder:
            painter.setPen(QColor("#78869b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder)
