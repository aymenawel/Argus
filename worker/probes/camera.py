"""Probe a webcam through DirectShow, and OpenCV's ArUco detector.

Camera: requests MJPEG at a target size, reads back the size and measured frame rate, then
tries to lock exposure and white balance and reads the properties back. Frames are measured
in memory only; nothing is saved. Usage: python -m probes.camera [index] [width] [height]

ArUco: draws the four Argus Card markers (DICT_4X4_50, IDs 0-3) on a page, warps it in
perspective, and checks that all four are detected.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import cv2
import numpy as np

from ._common import save

PROPS = {
    "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE,
    "exposure": cv2.CAP_PROP_EXPOSURE,
    "auto_wb": cv2.CAP_PROP_AUTO_WB,
    "wb_temperature": cv2.CAP_PROP_WB_TEMPERATURE,
    "autofocus": cv2.CAP_PROP_AUTOFOCUS,
    "gain": cv2.CAP_PROP_GAIN,
}


def _read_props(cap: cv2.VideoCapture) -> dict[str, float]:
    return {name: cap.get(prop) for name, prop in PROPS.items()}


def _measure_fps(cap: cv2.VideoCapture, frames: int = 45) -> tuple[float, tuple[int, int] | None, float]:
    shape = None
    brightness = []
    started = time.perf_counter()
    for _ in range(frames):
        ok, frame = cap.read()
        if ok:
            shape = (frame.shape[1], frame.shape[0])
            brightness.append(float(frame.mean()))
    elapsed = time.perf_counter() - started
    return frames / elapsed, shape, float(np.std(brightness)) if brightness else 0.0


def probe_camera(index: int, width: int, height: int) -> dict[str, Any]:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return {"index": index, "opened": False}
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # must come before the size
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little").decode(errors="replace")
    _measure_fps(cap, 10)  # warm-up
    fps_auto, shape, _ = _measure_fps(cap)
    before = _read_props(cap)

    requested = {"auto_exposure": 0.25, "exposure": before["exposure"], "auto_wb": 0, "wb_temperature": 4500}
    accepted = {name: bool(cap.set(PROPS[name], value)) for name, value in requested.items()}
    time.sleep(0.5)
    fps_locked, _, brightness_sd = _measure_fps(cap)
    after = _read_props(cap)
    cap.release()
    return {
        "index": index,
        "opened": True,
        "requested_size": [width, height],
        "fourcc": fourcc,
        "delivered_size": shape,
        "fps_measured_auto": round(fps_auto, 1),
        "fps_measured_after_lock": round(fps_locked, 1),
        "props_before": before,
        "set_accepted": accepted,
        "props_after": after,
        "brightness_sd_over_45_frames_after_lock": round(brightness_sd, 2),
    }


def probe_aruco() -> dict[str, Any]:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    page = np.full((1000, 1400), 255, np.uint8)
    corners_at = [(60, 60), (1140, 60), (60, 740), (1140, 740)]
    for marker_id, (x, y) in enumerate(corners_at):
        page[y : y + 200, x : x + 200] = cv2.aruco.generateImageMarker(dictionary, marker_id, 200)
    source = np.float32([[0, 0], [1400, 0], [1400, 1000], [0, 1000]])
    target = np.float32([[90, 40], [1300, 120], [1350, 950], [40, 900]])
    warped = cv2.warpPerspective(page, cv2.getPerspectiveTransform(source, target), (1400, 1000), borderValue=255)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(warped)
    return {
        "opencv_version": cv2.__version__,
        "detector_class": "cv2.aruco.ArucoDetector",
        "detected_ids": sorted(int(i) for i in ids.flatten()) if ids is not None else [],
        "marker_side_px_detected": [round(float(np.linalg.norm(c[0][0] - c[0][1])), 1) for c in corners],
    }


def main() -> None:
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 2560
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
    save("aruco", probe_aruco())
    save(f"camera_{index}", probe_camera(index, width, height))


if __name__ == "__main__":
    main()
