import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from argus.calibration.card import STANDARD
from argus.calibration.colour import correct_lab, neutral_drift, read_patches
from argus.calibration.detect import detect_card
from tests.helpers import scene


def rgb_to_lab(rgb: tuple[int, int, int]) -> np.ndarray:
    return rgb2lab(np.array([[rgb]], np.float64) / 255.0)[0, 0]


def _lab(reference, name: str) -> np.ndarray:
    return np.array(next(p.lab for p in reference.patches if p.name == name))


def test_patches_read_close_to_their_printed_colour():
    img = scene(STANDARD, 6.0)
    ref = read_patches(img, detect_card(img))
    for p, spec_patch in zip(ref.patches, STANDARD.patches(), strict=True):
        assert deltaE_ciede2000(np.array(p.lab), rgb_to_lab(spec_patch.rgb)) < 2.0


def test_dimmer_light_shows_as_drift_and_is_corrected():
    img = scene(STANDARD, 6.0)
    d = detect_card(img)
    ref = read_patches(img, d)
    cur = read_patches((img * 0.85).astype(np.uint8), d)
    assert neutral_drift(ref, cur) > 3.0
    assert deltaE_ciede2000(correct_lab(_lab(cur, "neutral_60"), ref, cur), _lab(ref, "neutral_60")) < 3.0
