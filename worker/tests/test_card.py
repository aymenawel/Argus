"""The Argus Card must be detectable, measure true millimetres, and print at the size its spec says."""

import re
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest

from argus.calibration.card import CARDS, COMPACT, STANDARD, aruco_dictionary, render_raster, render_sheet_svg

PX_PER_MM = 8.0


def _detect(image: np.ndarray) -> dict[int, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(aruco_dictionary(), cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(gray)
    return {} if ids is None else {int(i): c.reshape(4, 2) for i, c in zip(ids.flatten(), corners, strict=True)}


def _with_margin(image: np.ndarray, margin_px: int = 40) -> np.ndarray:
    return cv2.copyMakeBorder(
        image, margin_px, margin_px, margin_px, margin_px, cv2.BORDER_CONSTANT, value=(255, 255, 255)
    )


def test_card_ids_do_not_overlap_between_sizes() -> None:
    assert set(STANDARD.marker_ids).isdisjoint(COMPACT.marker_ids)


@pytest.mark.parametrize("spec", CARDS, ids=lambda s: s.name)
def test_elements_stay_inside_card_with_marker_quiet_zone(spec) -> None:
    module = spec.marker_size_mm / 6
    for marker in spec.markers():
        assert marker.x_mm >= module and marker.y_mm >= module
        assert marker.x_mm + marker.size_mm <= spec.width_mm - module
        assert marker.y_mm + marker.size_mm <= spec.height_mm - module
        for patch in spec.patches():
            gap_x = max(patch.x_mm - (marker.x_mm + marker.size_mm), marker.x_mm - (patch.x_mm + patch.size_mm))
            gap_y = max(patch.y_mm - (marker.y_mm + marker.size_mm), marker.y_mm - (patch.y_mm + patch.size_mm))
            assert max(gap_x, gap_y) >= module, f"patch {patch.name} too close to marker {marker.id}"


@pytest.mark.parametrize("spec", CARDS, ids=lambda s: s.name)
def test_rendered_card_markers_are_detected_with_spec_ids(spec) -> None:
    found = _detect(_with_margin(render_raster(spec, PX_PER_MM)))
    assert sorted(found) == sorted(spec.marker_ids)


@pytest.mark.parametrize("spec", CARDS, ids=lambda s: s.name)
def test_homography_from_markers_recovers_millimetres_under_perspective(spec) -> None:
    card = _with_margin(render_raster(spec, PX_PER_MM), 0)
    h, w = card.shape[:2]
    tilt = cv2.getPerspectiveTransform(
        np.float32([[0, 0], [w, 0], [w, h], [0, h]]),
        np.float32([[60, 30], [w + 20, 70], [w - 10, h + 40], [30, h + 10]]),
    )
    tilted = cv2.warpPerspective(card, tilt, (w + 120, h + 120), borderValue=(255, 255, 255))
    found = _detect(tilted)

    image_pts = np.concatenate([found[m.id] for m in spec.markers()])
    card_pts = np.concatenate([m.corners_mm() for m in spec.markers()])
    image_to_card, _ = cv2.findHomography(image_pts, card_pts)

    # Project the true positions of every patch centre through the tilt, then back to card mm.
    centres_mm = np.float32([[p.x_mm + p.size_mm / 2, p.y_mm + p.size_mm / 2] for p in spec.patches()])
    centres_px = cv2.perspectiveTransform((centres_mm * PX_PER_MM)[None], tilt)
    recovered_mm = cv2.perspectiveTransform(centres_px, image_to_card)[0]
    assert np.abs(recovered_mm - centres_mm).max() < 0.15


@pytest.mark.parametrize("spec", CARDS, ids=lambda s: s.name)
def test_patch_colours_render_as_specified(spec) -> None:
    card = render_raster(spec, PX_PER_MM)
    for patch in spec.patches():
        inset = patch.size_mm * 0.2
        x0, y0 = round((patch.x_mm + inset) * PX_PER_MM), round((patch.y_mm + inset) * PX_PER_MM)
        x1 = round((patch.x_mm + patch.size_mm - inset) * PX_PER_MM)
        y1 = round((patch.y_mm + patch.size_mm - inset) * PX_PER_MM)
        mean_bgr = card[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
        assert np.allclose(mean_bgr[::-1], patch.rgb, atol=1), patch.name


def _mm(value: str) -> float:
    match = re.fullmatch(r"([\d.]+)mm", value)
    assert match, value
    return float(match.group(1))


@pytest.mark.parametrize(("paper", "size_mm"), [("letter", (215.9, 279.4)), ("a4", (210.0, 297.0))])
def test_sheet_svg_has_physical_page_size_and_every_marker(paper, size_mm) -> None:
    root = ET.fromstring(render_sheet_svg(paper))
    assert (_mm(root.get("width")), _mm(root.get("height"))) == size_mm
    marker_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g") if (g.get("id") or "").startswith("marker-")]
    assert sorted(int(g.get("id").split("-")[1]) for g in marker_groups) == sorted(
        STANDARD.marker_ids + COMPACT.marker_ids
    )
