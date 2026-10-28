import time
import numpy as np
from memecam.config.settings import ROOT, DEFAULTS
from memecam.overlays.asset_manager import AssetManager
from memecam.gestures.mappings import load_mappings
from memecam.camera.pipeline import Pipeline


class FakeCamera:
    """Camera seam for exercising the real threaded pipeline without hardware."""
    def __init__(self, settings):
        self.error = None
        self.serial = 0
        self.released = False

    def start(self):
        pass

    def take(self, previous):
        time.sleep(.008)
        self.serial += 1
        return self.serial, time.monotonic(), np.zeros((180,320,3),np.uint8)

    def stop(self):
        self.released = True
        return True


def test_threaded_pipeline_commands_clean_debug_mailbox_and_shutdown(qapp, monkeypatch):
    import memecam.camera.pipeline as module
    monkeypatch.setattr(module, "CameraManager", FakeCamera)
    assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
    mappings = load_mappings(ROOT / "config/gestures.json", assets.images)
    settings = DEFAULTS | dict(hands=False, face=False, debug=True)
    worker = Pipeline(settings, assets, mappings)
    errors = []
    worker.error.connect(errors.append)
    worker.command("trigger", "approved")
    worker.start()
    deadline = time.monotonic() + 10
    packet = None
    try:
        while time.monotonic() < deadline:
            qapp.processEvents()
            packet = worker.take()
            if packet:
                break
            time.sleep(.02)
        assert packet is not None, errors
        clean, debug, status = packet
        assert status["active"] == ["approved"]
        assert status["fps"] > 0
        assert not np.array_equal(clean, debug)
        assert not clean[:36].any()  # Debug text belongs only to the preview.
        worker.command("clear")
        time.sleep(.1)
        packet = worker.take()
        assert packet is not None and not packet[2]["active"]
        assert worker.take() is None  # The mailbox is drained, never a stale-frame queue.
    finally:
        worker.stop()
        assert worker.wait(5000)
    qapp.processEvents()
    assert worker.capture.released
    assert not errors


def test_camera_failure_leaves_worker_stopped(qapp, monkeypatch):
    import memecam.camera.pipeline as module

    class BrokenCamera(FakeCamera):
        def start(self):
            self.error = "Test camera disconnected"

    monkeypatch.setattr(module, "CameraManager", BrokenCamera)
    assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
    worker = Pipeline(DEFAULTS | dict(hands=False,face=False), assets, {})
    errors = []
    worker.error.connect(errors.append)
    worker.start()
    assert worker.wait(5000)
    qapp.processEvents()
    assert errors == ["Test camera disconnected"]
    assert worker.capture.released
