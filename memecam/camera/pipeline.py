"""Dedicated processing worker. GUI polls a single-slot rendered-frame mailbox."""
import logging
import queue
import threading
import time
from contextlib import ExitStack
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from memecam.camera.camera_manager import CameraManager
from memecam.config.settings import ROOT
from memecam.gestures.gesture_engine import GestureEngine
from memecam.gestures.mappings import dispatch
from memecam.gestures.facial import classify
from memecam.overlays.overlay_engine import OverlayEngine
from memecam.vision.gesture_classifier import GestureClassifier
from memecam.vision.smoothing import PoseSmoother

LOG = logging.getLogger(__name__)
HAND_EDGES = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),
              (10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(0,17),
              (17,18),(18,19),(19,20)]


class Pipeline(QThread):
    error = Signal(str)
    ready = Signal()

    def __init__(self, settings, assets, mappings, facial_rules=None):
        super().__init__()
        self.settings = settings.copy()
        self.engine = OverlayEngine(assets.items, assets.images)
        self.mappings = mappings
        self.facial_rules = facial_rules or []
        self.setup_open = False
        self.preview_open = False
        self.commands = queue.Queue()
        self.lock = threading.Lock()
        self.packet = None
        self.capture = None
        self.capture_stuck = False
        self.processed_count = 0

    def command(self, *args):
        self.commands.put(args)

    def take(self):
        with self.lock:
            packet, self.packet = self.packet, None
        return packet

    def stop(self):
        self.requestInterruption()

    def run(self):
        try:
            self._run()
        except Exception as exc:
            LOG.exception("Video pipeline error")
            self.error.emit(str(exc))
        finally:
            if self.capture is not None and not self.capture.stop():
                self.capture_stuck = True
                self.error.emit("Camera driver is not responding. Restart MemeCam before reopening the camera.")
            LOG.info("Pipeline stopped; processed %s frames", self.processed_count)

    def _run(self):
        from memecam.vision.hand_tracker import HandTracker
        from memecam.vision.face_tracker import FaceTracker
        s = self.settings
        gesture = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
        facial = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
        classifier = GestureClassifier()
        smoother = PoseSmoother(s["smoothing"], s["face_hold"])
        with ExitStack() as stack:
            trackers = {}

            def tracker(kind):
                if kind not in trackers:
                    path = ROOT / "assets" / "models" / (kind + "_landmarker.task")
                    if not path.exists():
                        raise RuntimeError(f"Missing {path.name}. Run: python scripts/setup_models.py")
                    try:
                        obj = (HandTracker if kind == "hand" else FaceTracker)(path)
                    except Exception as exc:
                        raise RuntimeError(f"MediaPipe {kind} initialization failed: {exc}") from exc
                    stack.callback(obj.close)
                    trackers[kind] = obj
                    LOG.info("Vision initialized: %s", kind)
                return trackers[kind]

            for key, kind in (("hands", "hand"), ("face", "face")):
                if s[key]:
                    tracker(kind)
            if self.isInterruptionRequested():
                return
            self.capture = CameraManager(s)
            self.capture.start()
            last_serial, timestamp, fps = 0, 0, 0.0
            last_processed = time.monotonic()
            waiting_since = last_processed
            started = False
            while not self.isInterruptionRequested():
                while True:
                    try:
                        command = self.commands.get_nowait()
                    except queue.Empty:
                        break
                    if command[0] == "setting":
                        s[command[1]] = command[2]
                        if command[1] == "hands":
                            gesture = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
                        if command[1] == "face":
                            smoother = PoseSmoother(s["smoothing"], s["face_hold"])
                            facial = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
                    elif command[0] == "facial_rules":
                        self.facial_rules = command[1]
                        facial = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
                    elif command[0] == "setup":
                        self.setup_open = command[1]
                        facial = GestureEngine(s["confirmation"], s["release"], s["cooldown"])
                    elif command[0] == "preview":
                        self.preview_open = command[1]
                    elif command[0] == "trigger":
                        self.engine.trigger(command[1], time.monotonic(), toggle=True)
                    elif command[0] == "clear":
                        self.engine.clear()
                    elif command[0] == "register":
                        self.engine.register(command[1], command[2])
                if self.capture.error:
                    raise RuntimeError(self.capture.error)
                packet = self.capture.take(last_serial)
                if packet is None:
                    if time.monotonic() - waiting_since > 8:
                        raise RuntimeError("Camera is not delivering frames. Stop and select another device.")
                    self.msleep(3)
                    continue
                last_serial, captured, frame = packet
                now = time.monotonic()
                waiting_since = now
                if not started:
                    self.ready.emit()
                    started = True
                if s["mirror"]:
                    frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                small = cv2.resize(frame, (s["detection_width"], max(1, int(h*s["detection_width"]/w))))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                timestamp = max(timestamp + 1, int(captured * 1000))
                world, hands, face_points, pose, scores = [], [], [], None, {}
                if s["hands"]:
                    world, hands = tracker("hand").detect(rgb, timestamp)
                if s["face"]:
                    pose, face_points = tracker("face").detect(rgb, timestamp, w, h)
                    scores = tracker("face").scores.copy()
                pose = smoother.update(pose, now)
                candidate = classifier.classify(world[0]) if world else None
                confirmed = gesture.update(candidate, now)
                if confirmed and confirmed in self.mappings and not self.setup_open:
                    dispatch(self.engine, self.mappings[confirmed], now)
                face_candidate = classify(self.facial_rules, scores) if not self.setup_open else None
                face_confirmed = facial.update(face_candidate, now)
                if face_confirmed:
                    rule = next(r for r in self.facial_rules if r["id"] == face_confirmed)
                    self.engine.trigger(rule["overlay"], now)
                setup_frame = None
                if self.setup_open:
                    from mediapipe.tasks.python.vision import FaceLandmarksConnections
                    setup_frame = frame.copy()
                    points = np.asarray(face_points, dtype=int)
                    for edge in FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION:
                        if max(edge.start, edge.end) < len(points):
                            cv2.line(setup_frame, tuple(points[edge.start]), tuple(points[edge.end]),
                                     (90, 190, 110), 1, cv2.LINE_AA)
                preview_frame = frame.copy() if self.preview_open else None
                clean = self.engine.render(frame, pose, now)
                done = time.monotonic()
                instant = 1 / max(done - last_processed, .001)
                fps = instant if not fps else fps * .9 + instant * .1
                last_processed = done
                self.processed_count += 1
                if self.processed_count == 30:
                    LOG.info("Video performance: %.1f FPS, %.0f ms processing, %sx%s", fps,
                             (done-captured)*1000, w, h)
                debug = clean
                if s["debug"]:
                    debug = clean.copy()
                    for hand in hands:
                        points = (hand[:, :2] * (w, h)).astype(int)
                        for a, b in HAND_EDGES:
                            cv2.line(debug, tuple(points[a]), tuple(points[b]), (120, 230, 60), 2)
                        for point in points:
                            cv2.circle(debug, tuple(point), 3, (240, 240, 240), -1)
                    for point in face_points:
                        cv2.circle(debug, tuple(np.asarray(point, dtype=int)), 1, (220, 160, 70), -1)
                    text = f"{fps:.1f} FPS | candidate: {candidate or '-'} {gesture.progress:.0%} | confirmed: {gesture.confirmed or '-'}"
                    cv2.rectangle(debug, (0, 0), (w, 36), (16, 16, 16), -1)
                    cv2.putText(debug, text, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, .55, (255,255,255), 1)
                with self.lock:
                    self.packet = (clean, debug, dict(fps=fps, candidate=candidate, progress=gesture.progress,
                                   confirmed=gesture.confirmed, face=pose is not None,
                                   hands=bool(world), latency=(done-captured)*1000,
                                   size=f"{w} × {h}", active=list(self.engine.active),
                                   face_scores=scores, face_candidate=face_candidate,
                                   face_progress=facial.progress, face_confirmed=facial.confirmed,
                                   setup_frame=setup_frame, pose=pose, preview_frame=preview_frame))
