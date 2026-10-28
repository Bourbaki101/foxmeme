import argparse
import logging
from logging.handlers import RotatingFileHandler
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from memecam.config.settings import ROOT, load_settings
from memecam.gestures.mappings import load_mappings
from memecam.overlays.asset_manager import AssetManager


def main():
    parser = argparse.ArgumentParser(description="MemeCam offline gesture studio")
    parser.add_argument("--demo", action="store_true", help="Synthetic preview; no camera access")
    parser.add_argument("--smoke-test", action="store_true", help="Verify UI and exit after 2 seconds")
    parser.add_argument("--start-camera", action="store_true", help="Start the saved camera after discovery")
    parser.add_argument("--quit-after", type=float, help="Exit after N seconds (diagnostics)")
    parser.add_argument("--screenshot", help="Save a synthetic-demo UI screenshot for layout inspection")
    args = parser.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    handlers = [RotatingFileHandler(ROOT / "logs/memecam.log", maxBytes=2_000_000,
                                    backupCount=3, encoding="utf-8")]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("MemeCam")
    app.setOrganizationName("MemeCam")
    try:
        settings, warning = load_settings(ROOT / "config/settings.json")
        assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
        mappings = load_mappings(ROOT / "config/gestures.json", {v.id for v in assets.items})
        from memecam.ui.main_window import MainWindow
        window = MainWindow(settings, assets, mappings, warning, demo=args.demo)
    except Exception as exc:
        logging.exception("Application startup failed")
        if args.smoke_test:
            raise
        QMessageBox.critical(None, "MemeCam startup error", str(exc))
        return 1
    window.show()
    demo_timer = None
    if args.demo:
        import cv2
        import numpy as np
        from memecam.overlays.overlay_engine import OverlayEngine
        from memecam.vision.smoothing import FacePose
        engine = OverlayEngine(assets.items, assets.images)
        engine.trigger("deal_glasses", 0)
        demo_timer = QTimer(window)
        tick = [0]

        def draw_demo():
            tick[0] += 1
            frame = np.full((720,1280,3), (34,28,22), np.uint8)
            cv2.circle(frame, (640,330), 165, (144,173,199), -1)
            cv2.circle(frame, (580,300), 10, (40,30,25), -1)
            cv2.circle(frame, (700,300), 10, (40,30,25), -1)
            cv2.ellipse(frame, (640,385), (55,25), 0, 0, 180, (60,55,50), 4)
            cv2.putText(frame, "SYNTHETIC DEMO", (35,665), cv2.FONT_HERSHEY_SIMPLEX, .7, (130,160,180), 1)
            engine.render(frame, FacePose(640,300,120,0,640,330,330), 0)
            window.preview.set_frame(frame)
            window.output.set_frame(frame)
        demo_timer.timeout.connect(draw_demo)
        demo_timer.start(33)
        draw_demo()
    if args.start_camera and not args.demo:
        window.discovery.discovered.connect(lambda _: QTimer.singleShot(0, window.start_camera))
    if args.smoke_test:
        window.open_output()
        QTimer.singleShot(1800, window.close)
    if args.screenshot and args.demo:
        from pathlib import Path
        destination = Path(args.screenshot).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        QTimer.singleShot(800, lambda: window.grab().save(str(destination)))
    if args.quit_after:
        QTimer.singleShot(int(args.quit_after * 1000), window.close)
    logging.info("Application started")
    result = app.exec()
    logging.info("Application closed")
    return result


if __name__ == "__main__":
    sys.exit(main())
