import math
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from memecam.vision.smoothing import FacePose


class FaceTracker:
    def __init__(self, model):
        self.scores = {}
        self.task = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO, num_faces=1,
            min_face_detection_confidence=.65, min_face_presence_confidence=.65,
            min_tracking_confidence=.65, output_face_blendshapes=True))

    def detect(self, rgb, timestamp, width, height):
        result = self.task.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
        self.scores = ({c.category_name: float(c.score) for c in result.face_blendshapes[0]
                        if c.category_name != "_neutral"} if result.face_blendshapes else {})
        if not result.face_landmarks:
            return None, []
        p = np.array([(v.x * width, v.y * height) for v in result.face_landmarks[0]])
        left, right = p[[33, 133]].mean(axis=0), p[[362, 263]].mean(axis=0)
        delta, mid = right - left, (left + right) / 2
        center = (p[234] + p[454]) / 2
        return FacePose(*mid, float(np.linalg.norm(delta)), math.atan2(delta[1], delta[0]),
                        *center, float(np.linalg.norm(p[454] - p[234]))), p

    def close(self):
        self.task.close()
