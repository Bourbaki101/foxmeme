import numpy as np
from PySide6.QtCore import Qt
from memecam.ui.output_window import OutputWindow
from memecam.ui.widgets.video_widget import VideoWidget
from memecam.config.settings import ROOT, DEFAULTS
from memecam.overlays.asset_manager import AssetManager


def test_output_owns_pixels_and_has_no_controls(qapp):
    output = OutputWindow()
    frame = np.full((180,320,3), 100, np.uint8)
    output.set_frame(frame)
    frame[:] = 0
    assert output.image.pixelColor(0,0).red() == 100
    assert not output.placeholder
    assert not output.findChildren(VideoWidget)
    output.configure(borderless=True)
    qapp.processEvents()
    assert output.windowFlags() & Qt.WindowType.FramelessWindowHint
    output.clear()
    assert output.image is None
    output.close()


def test_main_window_layout_keeps_gesture_text_inside_panel(qapp):
    from memecam.ui.main_window import MainWindow
    assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
    window = MainWindow(DEFAULTS.copy(),assets,{},demo=True)
    window.show()
    try:
        for width, height in ((1180,850),(960,700)):
            window.resize(width,height)
            qapp.processEvents()
            for label in window.gesture_labels.values():
                assert label.height() >= 36
                assert label.parentWidget().rect().contains(label.geometry())
            window.inspector.setCurrentIndex(1)
            qapp.processEvents()
            assert window.confirmed.parentWidget().rect().contains(window.confirmed.geometry())
            for control in (window.camera, window.resolution, window.fps_target,
                            window.checks["debug"], window.output_debug):
                assert control.isVisible()
                assert control.parentWidget().rect().contains(control.geometry())
            window.inspector.setCurrentIndex(0)
    finally:
        window.close()
        qapp.processEvents()
