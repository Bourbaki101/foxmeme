"""Validated JSON configuration and atomic persistence."""
import json
import logging
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger(__name__)
DEFAULTS = dict(camera=0, width=1280, height=720, fps=30, hands=True, face=True,
                debug=False, mirror=True, confirmation=0.35, release=0.25,
                cooldown=0.8, smoothing=0.3, face_hold=0.2, detection_width=640)
DEFAULTS.update(borderless=False, fullscreen=False)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        LOG.info("Configuration loaded: %s", path)
        return value
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temp.replace(path)


def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError("Settings must be a JSON object")
    result = DEFAULTS | value
    for key in ("hands", "face", "debug", "mirror", "borderless", "fullscreen"):
        if type(result[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    for key, low, high in (("camera", 0, 1000), ("width", 160, 3840), ("height", 120, 2160),
                           ("fps", 1, 120), ("detection_width", 160, 1280)):
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError(f"{key} must be an integer in {low}..{high}")
    for key, low, high in (("confirmation", .1, 3), ("release", .1, 3), ("cooldown", 0, 10),
                           ("smoothing", .01, 1), ("face_hold", 0, 1)):
        v = result[key]
        if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
    return {key: result[key] for key in DEFAULTS}


def load_settings(path):
    if not Path(path).exists():
        return DEFAULTS.copy(), None
    try:
        return validate_settings(read_json(path)), None
    except ValueError as exc:
        LOG.error("Configuration error: %s", exc)
        return DEFAULTS.copy(), str(exc)
