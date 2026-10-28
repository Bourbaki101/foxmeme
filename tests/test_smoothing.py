import math
import pytest
from memecam.vision.smoothing import FacePose, PoseSmoother


def pose(x=0, angle=0):
    return FacePose(x,10,30,angle,x,20,80)


def test_interpolation_and_face_loss():
    smoother = PoseSmoother(.25,.2)
    assert smoother.update(pose(0),0).x == 0
    assert smoother.update(pose(100),.1).x == 25
    assert smoother.update(None,.2).x == 25
    assert smoother.update(None,.31) is None
    assert smoother.update(pose(200),.4).x == 200


def test_angle_uses_short_path():
    smoother = PoseSmoother(.5,.2)
    smoother.update(pose(angle=math.radians(179)),0)
    value = smoother.update(pose(angle=math.radians(-179)),.1)
    assert value.angle == pytest.approx(math.pi)
