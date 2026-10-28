"""Exercise actual MediaPipe Tasks models with blank local frames; no camera."""
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memecam.config.settings import ROOT  # noqa: E402
from memecam.vision.hand_tracker import HandTracker  # noqa: E402
from memecam.vision.face_tracker import FaceTracker  # noqa: E402


def main():
    rgb = np.zeros((360,640,3),np.uint8)
    hand = HandTracker(ROOT / "assets/models/hand_landmarker.task")
    try:
        world, image = hand.detect(rgb,1)
        assert world == [] and image == []
    finally:
        hand.close()
    face = FaceTracker(ROOT / "assets/models/face_landmarker.task")
    try:
        pose, points = face.detect(rgb,1,1280,720)
        assert pose is None and points == []
    finally:
        face.close()
    print("PASS: both local MediaPipe Tasks models loaded, inferred and closed")


if __name__ == "__main__":
    main()
