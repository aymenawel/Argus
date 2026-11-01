"""The change map (D-92): what changed in a vessel since its start, found by code alone."""

import numpy as np

from argus.segment.change import MAX_REGIONS, change_reference, change_regions

SIZE, CENTRE, RADIUS = 120, (60, 60), 50
YY, XX = np.mgrid[:SIZE, :SIZE]


def disc(cx, cy, r):
    return (XX - cx) ** 2 + (YY - cy) ** 2 <= r**2


def agar(seed):
    """A grey agar crop with a little camera noise in each channel."""
    noise = np.random.default_rng(seed).normal(0.0, 1.5, (SIZE, SIZE, 3))
    return np.clip(90.0 + noise, 0, 255).astype(np.uint8)


def raised(crop, where, by):
    out = crop.astype(np.int16)
    out[where] += by
    return np.clip(out, 0, 255).astype(np.uint8)


VESSEL = disc(*CENTRE, RADIUS)
ROI = ((10.0, 10.0), (110.0, 10.0), (110.0, 110.0), (10.0, 110.0))


def reference(vessel=VESSEL):
    return change_reference([agar(1), agar(2), agar(3)], vessel, ROI)


def test_a_faint_growing_patch_is_found():
    patch = disc(70, 60, 15)
    regions = change_regions(reference(), raised(agar(4), patch, 40))
    assert len(regions) == 1
    x0, y0, x1, y1 = regions[0].box
    assert x0 <= 55 and y0 <= 45 and x1 >= 85 and y1 >= 75
    px, py = regions[0].peak
    assert patch[py, px]
    assert regions[0].mask.shape == (SIZE, SIZE) and regions[0].mask[60, 70]


def test_noise_alone_changes_nothing():
    assert change_regions(reference(), agar(4)) == []


def test_light_changing_everywhere_is_not_growth():
    """Raised by 40 everywhere, the whole vessel would pass the core threshold: only the correction from the pixels
    outside the vessel keeps it out."""
    assert change_regions(reference(), raised(agar(4), np.ones((SIZE, SIZE), bool), 40)) == []


def test_a_speck_below_the_size_floor_is_dropped():
    speck = np.zeros((SIZE, SIZE), bool)
    speck[59:62, 59:62] = True
    assert change_regions(reference(), raised(agar(4), speck, 80)) == []


def test_strong_specks_scattered_in_a_faint_band_are_not_growth():
    """Scan streaks put single strong pixels into a band of faint change: a core needs some size to seed a region."""
    band = (YY >= 30) & (YY < 50)
    specks = np.zeros((SIZE, SIZE), bool)
    specks[40, 30:90:12] = True
    crop = raised(raised(agar(4), band, 20), specks, 80)  # the band is above the fringe, below the core
    assert change_regions(reference(), crop) == []


def test_the_rim_is_left_out():
    ring = disc(*CENTRE, RADIUS) & ~disc(*CENTRE, 48)
    assert change_regions(reference(), raised(agar(4), ring, 80)) == []


def test_a_vessel_filling_its_crop_skips_the_light_correction():
    everywhere = np.ones((SIZE, SIZE), bool)
    regions = change_regions(reference(everywhere), raised(agar(4), disc(70, 60, 15), 40))
    assert len(regions) == 1


def test_at_most_sixteen_regions_largest_first():
    squares = np.zeros((SIZE, SIZE), bool)
    for i, (x, y) in enumerate((x, y) for y in (35, 50, 65, 80) for x in (30, 45, 60, 75, 90)):
        side = 6 + i // 4
        squares[y : y + side, x : x + side] = True
    regions = change_regions(reference(), raised(agar(4), squares, 60))
    assert len(regions) == MAX_REGIONS
    areas = [int(r.mask.sum()) for r in regions]
    assert areas == sorted(areas, reverse=True)
