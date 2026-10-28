from dataclasses import dataclass, asdict
from pathlib import Path
import math


@dataclass(frozen=True)
class Overlay:
    id: str
    name: str
    file: str
    type: str = "png"
    anchor: str = "bottom"
    duration: float = 2.0
    scale: float = .5
    offset_x: float = 0
    offset_y: float = 0
    rotation_mode: str = "none"
    tracking_mode: str = "screen"

    @classmethod
    def parse(cls, data):
        try:
            item = cls(**data)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid overlay: {exc}") from exc
        if not all(isinstance(getattr(item, k), str) and getattr(item, k) for k in
                   ("id", "name", "file", "type", "anchor", "rotation_mode", "tracking_mode")):
            raise ValueError("Overlay text fields must be nonempty strings")
        if Path(item.file).name != item.file or Path(item.file).suffix.lower() != ".png":
            raise ValueError("Overlay file must be a PNG filename inside the library")
        if item.type != "png" or item.tracking_mode not in ("eyes", "face", "screen"):
            raise ValueError("Unsupported overlay type or tracking mode")
        if item.anchor not in ("center", "bottom", "top") or item.rotation_mode not in ("none", "face"):
            raise ValueError("Invalid anchor or rotation mode")
        for key in ("duration", "scale", "offset_x", "offset_y"):
            v = getattr(item, key)
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ValueError(f"Invalid overlay {key}")
        if not 0 <= item.duration <= 3600 or not .01 <= item.scale <= 5:
            raise ValueError("Overlay duration/scale outside supported range")
        if max(abs(item.offset_x), abs(item.offset_y)) > 2:
            raise ValueError("Offsets must be normalized values between -2 and 2")
        return item

    def json(self):
        return asdict(self)
