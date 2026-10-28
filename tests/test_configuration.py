import json
import cv2
import numpy as np
import pytest
from memecam.config.settings import DEFAULTS, ROOT, load_settings, validate_settings, write_json
from memecam.gestures.mappings import load_mappings, dispatch
from memecam.overlays.asset_manager import AssetManager
from memecam.overlays.overlay_model import Overlay


def test_settings_roundtrip_and_invalid_fallback(tmp_path):
    path = tmp_path / "settings.json"
    assert load_settings(path) == (DEFAULTS, None)
    write_json(path, DEFAULTS | {"camera":2, "hands":False})
    result, warning = load_settings(path)
    assert warning is None and result["camera"] == 2 and not result["hands"]
    path.write_text("{broken")
    assert load_settings(path)[1]


@pytest.mark.parametrize("change", [{"fps":0},{"camera":-1},{"hands":"yes"},
                                   {"smoothing":float("nan")},{"confirmation":0},{"width":True}])
def test_invalid_settings(change):
    with pytest.raises(ValueError):
        validate_settings(DEFAULTS | change)


def test_default_library_and_mappings():
    assets = AssetManager(ROOT / "assets/overlays", ROOT / "config/overlays.json")
    mappings = load_mappings(ROOT / "config/gestures.json", assets.images)
    assert len(assets.items) == 4 and len(mappings) == 5


@pytest.mark.parametrize("data", [[], {"bad":{}}, {"peace":{"action":"explode"}},
                                  {"peace":{"action":"show_overlay","overlay":"missing"}}])
def test_invalid_mapping(tmp_path, data):
    path = tmp_path / "gestures.json"
    write_json(path,data)
    with pytest.raises(ValueError):
        load_mappings(path, {"approved"})


@pytest.mark.parametrize("change", [{"file":"../escape.png"},{"duration":-1},{"scale":float("inf")},
                                   {"tracking_mode":"nose"},{"name":2},{"offset_x":999}])
def test_invalid_overlay(change):
    with pytest.raises(ValueError):
        Overlay.parse(dict(id="test",name="Test",file="test.png") | change)


def test_custom_import_persists_and_rejects_bad_image(tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    metadata = tmp_path / "overlays.json"
    write_json(metadata,[])
    source = tmp_path / "custom.png"
    source.write_bytes(cv2.imencode(".png",np.full((8,8,4),255,np.uint8))[1].tobytes())
    assets = AssetManager(library, metadata)
    item = assets.add(source,"Custom", "eyes", 0)
    restored = AssetManager(library, metadata)
    assert restored.items[0].id == item.id
    assert restored.items[0].duration == 0
    assert (library / item.file).exists()
    source.write_bytes(b"not a png")
    with pytest.raises(ValueError):
        assets.add(source,"Invalid")
    assert len(json.loads(metadata.read_text())) == 1


def test_dispatch():
    from memecam.overlays.overlay_engine import OverlayEngine
    engine = OverlayEngine([Overlay("a","A","a.png",duration=0)], {"a":np.zeros((1,1,4),np.uint8)})
    dispatch(engine,dict(action="toggle_overlay",overlay="a"),0)
    assert "a" in engine.active
    dispatch(engine,dict(action="clear_overlays"),1)
    assert not engine.active
