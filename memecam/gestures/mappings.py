from memecam.config.settings import read_json

GESTURES = ("peace", "thumbs_up", "thumbs_down", "open_palm", "fist")


def load_mappings(path, overlay_ids):
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("Gesture mappings must be an object")
    for gesture, mapping in data.items():
        if gesture not in GESTURES or not isinstance(mapping, dict):
            raise ValueError(f"Invalid gesture mapping: {gesture}")
        if mapping.get("action") not in ("toggle_overlay", "show_overlay", "clear_overlays"):
            raise ValueError(f"Invalid action for {gesture}")
        if mapping["action"] != "clear_overlays" and mapping.get("overlay") not in overlay_ids:
            raise ValueError(f"Unknown overlay for {gesture}")
    return data


def dispatch(engine, mapping, now):
    if mapping["action"] == "clear_overlays":
        engine.clear()
    else:
        engine.trigger(mapping["overlay"], now, toggle=mapping["action"] == "toggle_overlay")
