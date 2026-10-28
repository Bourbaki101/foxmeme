"""Hand-relative joint geometry, invariant to hand position, scale and mirroring."""
import numpy as np


def angle(a, b, c):
    u, v = a - b, c - b
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v) /
                 max(np.linalg.norm(u) * np.linalg.norm(v), 1e-9), -1, 1))))


class GestureClassifier:
    def classify(self, landmarks):
        p = np.asarray(landmarks, dtype=float)
        if p.shape != (21, 3) or not np.isfinite(p).all():
            return None
        palm = np.linalg.norm(p[0] - p[9])
        if palm < 1e-6:
            return None
        extended, folded = [], []
        for base in (5, 9, 13, 17):
            a = angle(p[base], p[base + 1], p[base + 3])
            reach = np.linalg.norm(p[base + 3] - p[0]) / max(np.linalg.norm(p[base + 1] - p[0]), 1e-6)
            extended.append(a > 155 and reach > 1.13)
            folded.append(a < 135 and reach < 1.13)
        thumb_straight = angle(p[1], p[2], p[4]) > 150 and angle(p[2], p[3], p[4]) > 150
        thumb_out = thumb_straight and np.linalg.norm(p[4] - p[5]) > .65 * palm
        if extended[0] and extended[1] and folded[2] and folded[3]:
            return "peace"
        if all(extended) and thumb_out:
            return "open_palm"
        if all(folded):
            delta = p[4] - p[2]
            if thumb_out and abs(delta[1]) > .35 * palm and abs(delta[1]) > 1.5 * abs(delta[0]):
                return "thumbs_up" if delta[1] < 0 else "thumbs_down"
            if not thumb_out and np.linalg.norm(p[4] - p[9]) < .9 * palm:
                return "fist"
        return None
