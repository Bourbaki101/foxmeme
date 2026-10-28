import logging
import math
import cv2
import numpy as np

LOG = logging.getLogger(__name__)


def composite(frame, image, x, y):
    """Clip all four edges before alpha blending, modifying only the affected ROI."""
    h, w = image.shape[:2]
    x, y = int(x - w / 2), int(y - h / 2)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    source = image[y0-y:y1-y, x0-x:x1-x]
    alpha = source[:, :, 3:4].astype(np.float32) / 255
    target = frame[y0:y1, x0:x1]
    target[:] = source[:, :, :3] * alpha + target * (1 - alpha)


class OverlayEngine:
    def __init__(self, items, images):
        self.items = {v.id: v for v in items}
        self.images = images.copy()
        self.active = {}

    def register(self, item, image):
        self.items[item.id], self.images[item.id] = item, image

    def trigger(self, identifier, now, toggle=False):
        if toggle and identifier in self.active:
            del self.active[identifier]
            LOG.info("Overlay removed: %s", identifier)
        else:
            duration = self.items[identifier].duration
            self.active[identifier] = now + duration if duration else None
            LOG.info("Overlay triggered: %s", identifier)

    def clear(self):
        self.active.clear()
        LOG.info("Overlays cleared")

    def expire(self, now):
        for key, end in list(self.active.items()):
            if end is not None and now >= end:
                del self.active[key]
                LOG.info("Overlay removed: %s", key)

    def render(self, frame, pose, now):
        self.expire(now)
        h, w = frame.shape[:2]
        for identifier in self.active:
            item, image = self.items[identifier], self.images[identifier]
            if item.tracking_mode != "screen" and pose is None:
                continue
            if item.tracking_mode == "eyes":
                x, y, width = pose.x, pose.y, pose.eye_distance * item.scale
            elif item.tracking_mode == "face":
                x, y, width = pose.center_x, pose.center_y, pose.width * item.scale
            else:
                width = w * item.scale
                overlay_h = width * image.shape[0] / image.shape[1]
                x = w / 2
                y = {"center": h / 2, "bottom": h - overlay_h / 2 - h * .06,
                     "top": overlay_h / 2 + h * .06}[item.anchor]
            x, y = x + item.offset_x * w, y + item.offset_y * h
            width = int(np.clip(width, 2, w * 3))
            height = max(1, int(width * image.shape[0] / image.shape[1]))
            scaled = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
            if pose is not None and item.rotation_mode == "face":
                # Positive image y points down; OpenCV's positive rotation is counterclockwise.
                degrees = -math.degrees(pose.angle)
                matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1)
                c, s = abs(matrix[0, 0]), abs(matrix[0, 1])
                rw, rh = int(height*s + width*c)+1, int(height*c + width*s)+1
                matrix[:, 2] += ((rw-width)/2, (rh-height)/2)
                scaled = cv2.warpAffine(scaled, matrix, (rw, rh))
            composite(frame, scaled, x, y)
        return frame
