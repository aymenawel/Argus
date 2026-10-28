import cv2
import numpy as np
import pytest

from argus.domain import Role, Vessel
from argus.segment import MaskPatch
from argus.segment.outline import outline_polygons
from argus.segment.tracking import TrackMatcher, assign_to_vessels

SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]


def disc_patch(cx: int, cy: int, r: int) -> MaskPatch:
    """A filled disc as a box-local patch placed at (cx - r, cy - r)."""
    local = np.zeros((2 * r + 1, 2 * r + 1), np.uint8)
    cv2.circle(local, (r, r), r, 1, -1)
    return MaskPatch(cx - r, cy - r, local.astype(bool))


def vessel(label: str, roi=SQUARE) -> Vessel:
    return Vessel(id=f"ves_{label}", run_id="run_1", label=label, role=Role.TREATMENT, roi=roi)


def test_outline_of_a_disc_is_a_closed_polygon_in_frame_pixels():
    [poly] = outline_polygons(disc_patch(150, 90, 30))
    xs, ys = zip(*poly, strict=True)
    assert 8 <= len(poly) <= 60
    assert min(xs) == pytest.approx(120, abs=2) and max(xs) == pytest.approx(180, abs=2)
    assert max(ys) == pytest.approx(120, abs=2)


def test_two_blobs_give_two_polygons_and_specks_are_dropped():
    local = np.zeros((60, 120), bool)
    local[10:40, 10:40] = True
    local[10:40, 70:100] = True
    local[55, 5] = True  # a one-pixel speck
    polys = outline_polygons(MaskPatch(100, 50, local))
    assert len(polys) == 2 and all(min(x for x, _ in p) >= 100 for p in polys)


def test_an_empty_patch_has_no_outline():
    assert outline_polygons(MaskPatch(0, 0, np.zeros((5, 5), bool))) == []


def test_patches_go_to_the_vessel_that_holds_most_of_them():
    a = vessel("A", roi=[(0, 0), (100, 0), (100, 200), (0, 200)])
    b = vessel("B", roi=[(100, 0), (200, 0), (200, 200), (100, 200)])
    patches = [disc_patch(50, 100, 20), disc_patch(160, 100, 20), disc_patch(100, 300, 10)]
    assert assign_to_vessels(patches, [a, b], (400, 200)) == {a.id: [0], b.id: [1]}


def test_a_patch_mostly_outside_every_vessel_goes_nowhere():
    a = vessel("A", roi=[(0, 0), (100, 0), (100, 100), (0, 100)])
    assert assign_to_vessels([disc_patch(110, 50, 20)], [a], (200, 200)) == {a.id: []}


def test_keys_follow_overlap_from_frame_to_frame():
    m, v = TrackMatcher(), vessel("A")
    first = m.match(v, "root", [disc_patch(50, 50, 10), disc_patch(120, 50, 10)])
    second = m.match(v, "root", [disc_patch(122, 52, 10), disc_patch(52, 50, 10), disc_patch(50, 150, 10)])
    assert first == ["A:root:1", "A:root:2"] and second == ["A:root:2", "A:root:1", "A:root:3"]


def test_keys_are_per_vessel_and_concept():
    m = TrackMatcher()
    assert m.match(vessel("A"), "root", [disc_patch(50, 50, 10)]) == ["A:root:1"]
    assert m.match(vessel("A"), "mung bean", [disc_patch(50, 50, 10)]) == ["A:mung bean:1"]
    assert m.match(vessel("B"), "root", [disc_patch(50, 50, 10)]) == ["B:root:1"]


def test_a_new_chunk_continues_the_previous_keys():
    m, v = TrackMatcher(), vessel("A")
    m.restore(v.id, "root", {"A:root:7": disc_patch(50, 50, 10)})
    assert m.match(v, "root", [disc_patch(51, 50, 10), disc_patch(150, 150, 10)]) == ["A:root:7", "A:root:8"]
