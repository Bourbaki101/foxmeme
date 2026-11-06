from copy import deepcopy
from dataclasses import replace
import time
import cv2
import numpy as np
import pytest
from memecam.config.settings import DEFAULTS, ROOT, write_json
from memecam.gestures.facial import learn_features, classify, match_score, load_rules, validate_rules
from memecam.overlays.asset_manager import AssetManager


def rule():
    return dict(id="smile", name="Sonrisa", overlay="approved", enabled=True, threshold=.65,
                features={"mouthSmileLeft": [.1, .9], "eyeBlinkLeft": [.8, .2]})


def test_expression_requires_all_features_and_supports_decreasing_values():
    r = rule()
    assert classify([r], {"mouthSmileLeft": .9, "eyeBlinkLeft": .2}) == "smile"
    assert match_score(r, {"mouthSmileLeft": .9, "eyeBlinkLeft": .8}) == 0
    assert classify([r], {"mouthSmileLeft": .9}) is None
    assert classify([r], {}) is None
    assert classify([r | {"enabled": False}], {"mouthSmileLeft": .9, "eyeBlinkLeft": .2}) is None
    assert classify([r], {"mouthSmileLeft": .1, "eyeBlinkLeft": .8}) is None


def test_learn_strongest_features_and_reject_neutral():
    neutral = {f"feature{i}": .1 for i in range(10)}
    assert len(learn_features(neutral, {k: .9 for k in neutral})) == 6
    with pytest.raises(ValueError, match="parecido"):
        learn_features(neutral, {k: .11 for k in neutral})


@pytest.mark.parametrize("change", [{"overlay": "missing"}, {"enabled": 1}, {"threshold": float("nan")},
                                    {"features": {}}, {"features": {"x": [0, .01]}},
                                    {"features": {"x": [0, float("inf")]}}, {"name": ""}])
def test_invalid_saved_expression(change):
    with pytest.raises(ValueError):
        validate_rules([rule() | change], {"approved"})


def test_expression_roundtrip_and_duplicate_ids(tmp_path):
    path = tmp_path / "facial.json"
    assert load_rules(path, {"approved"}) == []
    write_json(path, [rule()])
    assert load_rules(path, {"approved"}) == [rule()]
    with pytest.raises(ValueError):
        validate_rules([rule(), deepcopy(rule())], {"approved"})


def test_rgb_image_import_and_placement_persist(tmp_path):
    source = tmp_path / "image.jpg"
    source.write_bytes(cv2.imencode(".jpg", np.full((12, 12, 3), 120, np.uint8))[1].tobytes())
    directory = tmp_path / "library"
    directory.mkdir()
    metadata = tmp_path / "overlays.json"
    write_json(metadata, [])
    assets = AssetManager(directory, metadata)
    item = assets.add(source, "Foto", "face", 0)
    assert assets.images[item.id].shape == (12, 12, 4)
    assert np.all(assets.images[item.id][:, :, 3] == 255)
    updated = replace(item, scale=1.3, offset_y=-.1, rotation_mode="face")
    assets.update(updated)
    assert AssetManager(directory, metadata).items == [updated]


def test_setup_capture_save_and_reload(qapp, tmp_path, monkeypatch):
    from memecam.ui.main_window import MainWindow
    import memecam.ui.face_setup as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source = tmp_path / "sample.png"
    source.write_bytes(cv2.imencode(".png", np.full((8, 8, 4), 255, np.uint8))[1].tobytes())
    library = tmp_path / "library"
    library.mkdir()
    metadata = tmp_path / "overlays.json"
    write_json(metadata, [])
    assets = AssetManager(library, metadata)
    item = assets.add(source, "Test", "face")
    window = MainWindow(DEFAULTS.copy(), assets, {}, demo=True)
    window.facial_rules = []
    window.open_face_setup()
    setup = window.face_setup
    try:
        frame = np.zeros((180, 320, 3), np.uint8)

        def feed(scores):
            setup.update_frame(frame, {"face_scores": scores, "setup_frame": frame})

        feed({"jawOpen": .05})
        setup.begin_capture("neutral")
        for _ in range(6):
            feed({"jawOpen": .05})
        setup.capture = ("neutral", time.monotonic() - 1.1)
        feed({"jawOpen": .05})
        setup.begin_capture("expression")
        for _ in range(6):
            feed({"jawOpen": .9})
        setup.capture = ("expression", time.monotonic() - 1.1)
        feed({"jawOpen": .9})
        assert setup.features == {"jawOpen": [.05, .9]}
        setup.name.setText("Boca abierta")
        setup.save_rule()
        restored = load_rules(tmp_path / "config/facial_gestures.json", assets.images)
        assert restored[0]["overlay"] == item.id
        assert restored[0]["name"] == "Boca abierta"
        setup.clear_live()
        setup.begin_capture("neutral")
        assert setup.capture is None
        assert setup.video.image is None
    finally:
        setup.close()
        window.close()
        qapp.processEvents()


def test_pipeline_setup_suppresses_automatic_trigger_then_rearms(qapp, monkeypatch):
    from memecam.camera.pipeline import Pipeline
    import memecam.camera.pipeline as module
    import memecam.vision.face_tracker as face_module
    from memecam.vision.smoothing import FacePose
    from test_pipeline import FakeCamera

    class FakeFace:
        def __init__(self, model):
            self.scores = {}

        def detect(self, rgb, timestamp, width, height):
            self.scores = {"mouthSmileLeft": .9, "eyeBlinkLeft": .2}
            return FacePose(160, 80, 50, 0, 160, 90, 100), np.full((478, 2), 40)

        def close(self):
            pass

    monkeypatch.setattr(module, "CameraManager", FakeCamera)
    monkeypatch.setattr(face_module, "FaceTracker", FakeFace)
    assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
    worker = Pipeline(DEFAULTS | dict(hands=False, confirmation=.1, cooldown=0), assets, {}, [rule()])
    worker.command("setup", True)
    worker.command("preview", True)
    errors = []
    worker.error.connect(errors.append)
    worker.start()

    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            qapp.processEvents()
            packet = worker.take()
            if packet and predicate(packet):
                return packet
            time.sleep(.02)
        pytest.fail(f"Pipeline did not reach expected state: {errors}")

    try:
        packet = wait_for(lambda p: p[2]["setup_frame"] is not None)
        assert packet[2]["active"] == []
        assert packet[2]["face_scores"]
        assert packet[2]["face_candidate"] is None
        assert packet[2]["setup_frame"].any() and not packet[0].any()
        assert packet[2]["pose"] is not None
        assert not packet[2]["preview_frame"].any()
        worker.command("preview", False)
        worker.command("setup", False)
        packet = wait_for(lambda p: "approved" in p[2]["active"])
        assert packet[2]["face_confirmed"] == "smile"
        assert packet[2]["preview_frame"] is None
        worker.command("clear")
        wait_for(lambda p: not p[2]["active"])
        time.sleep(.2)
        packet = wait_for(lambda p: p[2]["face_candidate"] == "smile")
        assert not packet[2]["active"]  # Holding a gesture cannot retrigger after manual clear.
        worker.command("setting", "face", False)
        packet = wait_for(lambda p: not p[2]["face_scores"])
        assert packet[2]["face_candidate"] is None
    finally:
        worker.stop()
        assert worker.wait(5000)
    qapp.processEvents()
    assert not errors
