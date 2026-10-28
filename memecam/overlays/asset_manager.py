import uuid
import cv2
import numpy as np
from memecam.config.settings import read_json, write_json
from memecam.overlays.overlay_model import Overlay


def read_png(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] != 4:
        raise ValueError(f"{path.name}: select a PNG with an alpha channel")
    if max(image.shape[:2]) > 8192:
        raise ValueError("PNG exceeds 8192 pixels; resize it before importing")
    return image


def read_import_image(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or image.dtype != np.uint8:
        raise ValueError("Select an 8-bit PNG, JPG or WebP image")
    if max(image.shape[:2]) > 8192:
        raise ValueError("Image exceeds 8192 pixels; resize it before importing")
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    if image.shape[2] != 4:
        raise ValueError("Unsupported image channels")
    return image


class AssetManager:
    def __init__(self, directory, metadata):
        self.directory, self.metadata = directory, metadata
        data = read_json(metadata)
        if not isinstance(data, list):
            raise ValueError("Overlay library must be a JSON list")
        self.items = [Overlay.parse(v) for v in data]
        if len({v.id for v in self.items}) != len(self.items):
            raise ValueError("Overlay IDs must be unique")
        self.images = {v.id: read_png(directory / v.file) for v in self.items}

    def add(self, source, name, tracking="screen", duration=2.0):
        image = read_import_image(source)
        identifier = uuid.uuid4().hex
        item = Overlay.parse(dict(id=identifier, name=name, file=identifier + ".png",
                                 tracking_mode=tracking, duration=duration,
                                 scale={"eyes": 2.4, "face": 1.0, "screen": .5}.get(tracking, .5),
                                 anchor="center" if tracking != "screen" else "bottom",
                                 rotation_mode="face" if tracking != "screen" else "none"))
        destination = self.directory / item.file
        destination.write_bytes(cv2.imencode(".png", image)[1].tobytes())
        try:
            write_json(self.metadata, [v.json() for v in self.items + [item]])
        except OSError:
            destination.unlink(missing_ok=True)
            raise
        self.items.append(item)
        self.images[item.id] = image
        return item

    def update(self, item):
        item = Overlay.parse(item.json())
        if item.id not in self.images:
            raise ValueError("Unknown overlay")
        items = [item if v.id == item.id else v for v in self.items]
        write_json(self.metadata, [v.json() for v in items])
        self.items = items
