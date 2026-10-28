import numpy as np
import pytest
from memecam.gestures.gesture_engine import GestureEngine
from memecam.vision.gesture_classifier import GestureClassifier


def test_confirmation_hold_release_and_repeat():
    engine = GestureEngine(.35, .25, .8)
    assert engine.update("peace", 0) is None
    assert engine.update("peace", .34) is None
    assert engine.progress == pytest.approx(.34/.35)
    assert engine.update("peace", .36) == "peace"
    for now in np.linspace(.4, 4, 120):
        assert engine.update("peace", now) is None
    assert engine.update(None, 4.1) is None
    assert engine.update(None, 4.4) is None
    assert engine.update("peace", 4.5) is None
    assert engine.update("peace", 4.86) == "peace"


def test_single_frame_and_changed_candidate_never_confirm():
    engine = GestureEngine()
    assert engine.update("peace", 0) is None
    assert engine.update(None, .1) is None
    assert engine.update("fist", .2) is None
    assert engine.update("peace", .4) is None
    assert engine.update("peace", .6) is None
    assert engine.update(None, .7) is None


def test_cooldown_and_brief_dropout():
    engine = GestureEngine(.3, .25, 1)
    engine.update("peace", 0)
    assert engine.update("peace", .31) == "peace"
    engine.update(None, .4)
    assert engine.update("peace", .5) is None
    assert engine.update("peace", 2) is None
    engine.update("fist", 2.1)
    engine.update("fist", 2.4)
    assert engine.update("fist", 2.41) == "fist"
    engine.update(None, 2.45)
    engine.update(None, 2.71)
    engine.update("peace", 2.72)
    assert engine.update("peace", 3.05) is None
    assert engine.update("peace", 3.42) == "peace"


def hand_fixture(gesture):
    # Isotropic local hand coordinates, wrist at origin, fingers upwards.
    p = np.zeros((21, 3))
    for j, x in enumerate((-.5, 0, .45, .8)):
        base = 5 + j*4
        p[base] = (x,-1,0)
        p[base+1] = (x,-1.6,0)
        straight = gesture == "open_palm" or gesture == "peace" and j < 2
        if straight:
            p[base+2], p[base+3] = (x,-2.1,0), (x,-2.6,0)
        else:
            p[base+2], p[base+3] = (x,-1.1,.1), (x,-.8,.1)
    if gesture in ("thumbs_up", "thumbs_down"):
        direction = -1 if gesture == "thumbs_up" else 1
        p[1], p[2], p[3], p[4] = [(-1.3, direction*y,0) for y in (.3,.6,1,1.5)]
    elif gesture in ("peace", "fist"):
        p[1], p[2], p[3], p[4] = (-.8,-.4,0),(-1,-.8,0),(-.5,-1,0),(0,-.8,0)
    else:
        p[1], p[2], p[3], p[4] = (-.4,-.3,0),(-.8,-.6,0),(-1.2,-.9,0),(-1.6,-1.2,0)
    return p


@pytest.mark.parametrize("gesture", ["peace", "fist", "thumbs_up", "thumbs_down", "open_palm"])
@pytest.mark.parametrize("mirror", [1, -1])
def test_synthetic_classifier(gesture, mirror):
    p = hand_fixture(gesture)
    p[:,0] *= mirror
    assert GestureClassifier().classify(p*.13 + (2,3,1)) == gesture


def test_degenerate_and_ambiguous_hands():
    classifier = GestureClassifier()
    assert classifier.classify(np.zeros((21,3))) is None
    assert classifier.classify(np.full((21,3), np.nan)) is None
    p = hand_fixture("peace")
    p[9:13] = hand_fixture("fist")[9:13]
    assert classifier.classify(p) is None
