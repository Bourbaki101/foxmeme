import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandTracker:
    def __init__(self, model):
        self.task = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=.7, min_hand_presence_confidence=.7,
            min_tracking_confidence=.7))

    def detect(self, rgb, timestamp):
        result = self.task.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
        # World coordinates have metric/isotropic axes; image-normalized x/y do not.
        world = [np.array([(p.x, p.y, p.z) for p in hand]) for hand in result.hand_world_landmarks]
        image = [np.array([(p.x, p.y, p.z) for p in hand]) for hand in result.hand_landmarks]
        return world, image

    def close(self):
        self.task.close()
