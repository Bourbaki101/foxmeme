import numpy as np
import pytest
from memecam.overlays.overlay_engine import OverlayEngine, composite
from memecam.overlays.overlay_model import Overlay
from memecam.vision.smoothing import FacePose


def make_engine():
    image = np.full((20,80,4), 255, dtype=np.uint8)
    return OverlayEngine([Overlay("temp", "Temporary", "t.png", duration=2),
                          Overlay("eyes", "Eyes", "e.png", duration=0, tracking_mode="eyes",
                                  rotation_mode="face", scale=2.5)], {"temp":image, "eyes":image})


def test_lifetime_toggle_and_clear():
    engine = make_engine()
    engine.trigger("temp", 1)
    engine.trigger("eyes", 1, toggle=True)
    engine.expire(2.99)
    assert set(engine.active) == {"temp", "eyes"}
    engine.expire(3)
    assert set(engine.active) == {"eyes"}
    engine.expire(1000)
    assert "eyes" in engine.active
    engine.trigger("eyes", 1000, toggle=True)
    assert not engine.active
    engine.trigger("eyes", 1001)
    engine.trigger("temp", 1001)
    engine.clear()
    assert not engine.active


def test_retrigger_restarts_temporary_lifetime():
    engine = make_engine()
    engine.trigger("temp", 0)
    engine.trigger("temp", 1)
    engine.expire(2.5)
    assert "temp" in engine.active
    engine.expire(3)
    assert not engine.active


@pytest.mark.parametrize("x,y", [(0,0),(10,0),(0,10),(10,10),(-100,-100),(100,100)])
def test_composite_clips_without_crashing(x,y):
    frame = np.zeros((10,10,3), dtype=np.uint8)
    image = np.full((10,10,4), 255, dtype=np.uint8)
    image[:,:,3] = 128
    composite(frame, image, x, y)
    assert frame.max() <= 128


def test_face_overlay_hidden_when_tracking_lost_and_rotates():
    engine = make_engine()
    engine.trigger("eyes",0)
    frame = np.zeros((100,200,3),dtype=np.uint8)
    assert not engine.render(frame.copy(),None,0).any()
    pose = FacePose(100,50,40,.5,100,50,90)
    assert engine.render(frame,pose,0).any()


def test_transparent_pixels_do_not_modify_frame():
    frame = np.full((10,10,3), 123, dtype=np.uint8)
    composite(frame, np.zeros((10,10,4),dtype=np.uint8), 5,5)
    assert np.all(frame == 123)
