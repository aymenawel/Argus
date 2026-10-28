import cv2
import pytest

from argus.capture.webcam import CameraSettings, list_cameras, open_webcam
from argus.domain import CameraProperty


class FakeCapture:
    """Stands in for cv2.VideoCapture: logs set() calls and answers get() from `readback` or the last set."""

    def __init__(self, readback=None, open_indexes=(0,), set_result=True):
        self.readback, self.open_indexes, self.set_result = readback or {}, open_indexes, set_result
        self.calls: list[int] = []
        self.values: dict[int, float] = {}
        self.index = None

    def __call__(self, index, api=None):
        self.index, self.api = index, api
        return self

    def isOpened(self):  # noqa: N802 (OpenCV's name)
        return self.index in self.open_indexes

    def set(self, prop, value):
        self.calls.append(prop)
        self.values[prop] = value
        return self.set_result

    def get(self, prop):
        return self.readback.get(prop, self.values.get(prop, -1))

    def release(self):
        pass


def test_read_back_decides_locked_not_locked_unknown():
    fake = FakeCapture(readback={cv2.CAP_PROP_EXPOSURE: -1, cv2.CAP_PROP_WB_TEMPERATURE: 4500})
    _, props = open_webcam(0, CameraSettings(exposure=-6, white_balance=4500), capture_factory=fake)
    assert props == {
        "exposure": CameraProperty.UNKNOWN,
        "white_balance": CameraProperty.LOCKED,
        "focus": CameraProperty.NOT_LOCKED,
    }
    assert fake.api == cv2.CAP_DSHOW


def test_a_value_that_reads_back_differently_is_not_locked():
    fake = FakeCapture(readback={cv2.CAP_PROP_FOCUS: 40})
    _, props = open_webcam(0, CameraSettings(focus=10), capture_factory=fake)
    assert props["focus"] is CameraProperty.NOT_LOCKED


def test_a_refused_set_is_unknown():
    _, props = open_webcam(0, CameraSettings(focus=10), capture_factory=FakeCapture(set_result=False))
    assert props["focus"] is CameraProperty.UNKNOWN


def test_mjpeg_is_requested_before_the_size():
    fake = FakeCapture()
    open_webcam(0, CameraSettings(), capture_factory=fake)
    order = fake.calls
    assert order.index(cv2.CAP_PROP_FOURCC) < order.index(cv2.CAP_PROP_FRAME_WIDTH)
    assert order.index(cv2.CAP_PROP_FOURCC) < order.index(cv2.CAP_PROP_FRAME_HEIGHT)


def test_a_camera_that_does_not_open_is_named():
    with pytest.raises(RuntimeError, match="camera 3 did not open"):
        open_webcam(3, CameraSettings(), capture_factory=FakeCapture(open_indexes=(0,)))


def test_list_cameras():
    assert list_cameras(max_index=4, capture_factory=FakeCapture(open_indexes=(0, 2))) == [0, 2]


def test_a_lock_needs_the_auto_switch_to_read_back_as_manual():
    # The exposure value reads back as asked, but the driver can't say auto exposure is off (-1): not proven.
    fake = FakeCapture(readback={cv2.CAP_PROP_AUTO_EXPOSURE: -1, cv2.CAP_PROP_AUTO_WB: 1})
    _, props = open_webcam(0, CameraSettings(exposure=-6, white_balance=4500), capture_factory=fake)
    assert props["exposure"] is CameraProperty.UNKNOWN  # switch unreadable
    assert props["white_balance"] is CameraProperty.NOT_LOCKED  # switch still on auto
