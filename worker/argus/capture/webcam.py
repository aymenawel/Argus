"""Webcams through DirectShow, with exposure, white balance and focus locks read back (KB 09).

A True from VideoCapture.set() proves nothing: each requested lock is recorded as locked, not locked or
unknown from what the driver reports afterwards, so the run record says honestly what was fixed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import cv2

from argus.domain import CameraProperty


@dataclass(frozen=True)
class CameraSettings:
    width: int = 1280
    height: int = 720
    fps: int = 30
    exposure: float | None = None  # DirectShow: negative log2 seconds, e.g. -6
    white_balance: int | None = None  # kelvin
    focus: int | None = None


# setting name -> (auto switch, its manual value, the value property)
LOCKS = {
    "exposure": (cv2.CAP_PROP_AUTO_EXPOSURE, 0.25, cv2.CAP_PROP_EXPOSURE),
    "white_balance": (cv2.CAP_PROP_AUTO_WB, 0, cv2.CAP_PROP_WB_TEMPERATURE),
    "focus": (cv2.CAP_PROP_AUTOFOCUS, 0, cv2.CAP_PROP_FOCUS),
}


def _read_back(capture: Any, prop: int, wanted: float, accepted: bool, auto: tuple[int, float]) -> CameraProperty:
    """Locked only when the value reads back as asked *and* the auto switch reads back as manual."""
    if not accepted:
        return CameraProperty.UNKNOWN
    auto_prop, manual = auto
    switch = capture.get(auto_prop)
    if switch == -1:  # the driver can't say whether automatic control is off
        return CameraProperty.UNKNOWN
    if abs(switch - manual) > 1e-6:
        return CameraProperty.NOT_LOCKED
    value = capture.get(prop)
    if value == -1:  # OpenCV's answer for a property the driver doesn't report
        return CameraProperty.UNKNOWN
    tolerance = max(abs(wanted) * 0.01, 1e-6)
    return CameraProperty.LOCKED if abs(value - wanted) <= tolerance else CameraProperty.NOT_LOCKED


def open_webcam(
    index: int, settings: CameraSettings, *, capture_factory: Callable[..., Any] = cv2.VideoCapture
) -> tuple[Any, dict[str, CameraProperty]]:
    capture = capture_factory(index, cv2.CAP_DSHOW)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"camera {index} did not open")
    # MJPEG before the size: otherwise DirectShow tends to pick raw YUY2 and a low frame rate at high resolution.
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
    capture.set(cv2.CAP_PROP_FPS, settings.fps)
    properties: dict[str, CameraProperty] = {}
    for name, (auto_prop, manual, prop) in LOCKS.items():
        wanted = getattr(settings, name)
        if wanted is None:
            properties[name] = CameraProperty.NOT_LOCKED
            continue
        capture.set(auto_prop, manual)
        properties[name] = _read_back(capture, prop, wanted, capture.set(prop, wanted), (auto_prop, manual))
    return capture, properties


def list_cameras(
    max_index: int = 4, *, skip: Sequence[int] = (), capture_factory: Callable[..., Any] = cv2.VideoCapture
) -> list[int]:
    """Camera indexes 0..max_index that open (indexes in `skip`, already open elsewhere, are not probed)."""
    found = []
    for index in range(max_index + 1):
        if index in skip:
            continue
        capture = capture_factory(index, cv2.CAP_DSHOW)
        if capture.isOpened():
            found.append(index)
        capture.release()
    return found
