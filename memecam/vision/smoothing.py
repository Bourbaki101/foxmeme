import math
from dataclasses import dataclass


@dataclass
class FacePose:
    x: float
    y: float
    eye_distance: float
    angle: float
    center_x: float
    center_y: float
    width: float


class PoseSmoother:
    def __init__(self, alpha=.3, hold=.2):
        self.alpha, self.hold = alpha, hold
        self.value = None
        self.last_seen = float("-inf")

    def update(self, pose, now):
        if pose is None:
            if now - self.last_seen > self.hold:
                self.value = None
            return self.value
        if self.value is None or now - self.last_seen > self.hold:
            self.value = pose
        else:
            old = self.value
            values = {k: getattr(old, k) * (1 - self.alpha) + getattr(pose, k) * self.alpha
                      for k in vars(pose) if k != "angle"}
            delta = math.atan2(math.sin(pose.angle - old.angle), math.cos(pose.angle - old.angle))
            self.value = FacePose(angle=old.angle + self.alpha * delta, **values)
        self.last_seen = now
        return self.value
