"""Camera discovery and a single-slot capture mailbox: slow consumers drop frames."""
import logging
import threading
import time
import cv2
from PySide6.QtCore import QThread, Signal

LOG = logging.getLogger(__name__)


class CameraDiscovery(QThread):
    discovered = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            from cv2_enumerate_cameras import enumerate_cameras
            cameras = [(c.index, c.name) for c in enumerate_cameras(cv2.CAP_DSHOW)]
            for index, name in cameras:
                LOG.info("Camera discovered: %s (%s)", name, index)
            self.discovered.emit(cameras)
        except Exception as exc:
            LOG.exception("Camera discovery failed")
            self.failed.emit(str(exc))


class CameraManager:
    def __init__(self, settings):
        self.settings = settings
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.serial = 0
        self.error = None
        self.thread = threading.Thread(target=self._capture, name="camera-capture", daemon=True)

    def start(self):
        self.thread.start()

    def _capture(self):
        cap = None
        try:
            s = self.settings
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                cap = cv2.VideoCapture(s["camera"], backend)
                if cap.isOpened():
                    break
                cap.release()
                LOG.warning("Camera %s did not open with backend %s", s["camera"], backend)
            if not cap.isOpened():
                raise RuntimeError("Cannot open camera. Close other camera apps and choose another device.")
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, s["width"])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, s["height"])
            cap.set(cv2.CAP_PROP_FPS, s["fps"])
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            LOG.info("Camera opened: %s, %sx%s at requested %s FPS", s["camera"],
                     cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT), s["fps"])
            failures = 0
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    failures += 1
                    if failures >= 10:
                        raise RuntimeError("Camera disconnected or stopped delivering frames. Reconnect and restart.")
                    self.stop_event.wait(.05)
                    continue
                failures = 0
                with self.lock:
                    self.serial += 1
                    self.latest = (self.serial, time.monotonic(), frame)
        except Exception as exc:
            self.error = str(exc)
            LOG.exception("Camera error")
        finally:
            if cap is not None:
                cap.release()
            LOG.info("Camera stopped")

    def take(self, previous):
        with self.lock:
            return self.latest if self.latest and self.latest[0] != previous else None

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)
        return not self.thread.is_alive()
