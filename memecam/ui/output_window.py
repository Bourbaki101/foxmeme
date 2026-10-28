from PySide6.QtCore import Qt
from memecam.ui.widgets.video_widget import VideoWidget


class OutputWindow(VideoWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MemeCam Output")
        self.resize(960, 540)

    def configure(self, borderless=False, fullscreen=False):
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, borderless)
        self.showFullScreen() if fullscreen else self.showNormal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
            self.showNormal()
        else:
            super().keyPressEvent(event)
