"""Published image sequences as a run source: a manifest names the frames, the dishes (tiles) and where the data
came from; the run keeps that provenance (D-70, D-71)."""

import json

import cv2
import numpy as np
import pytest

from argus.capture.images import ImageSequenceSource
from argus.datasets.manifest import ManifestError, load_manifest

PROVENANCE = {
    "dataset": "Test plates",
    "doi": "10.0000/test",
    "url": "https://example.org/plates",
    "licence": "CC BY 4.0",
    "credit": "Test Lab (2020)",
}


def write_manifest(folder, *, frames=3, skip=None, **overrides) -> str:
    """Frames of two 40×40 tiles side by side; `skip` names a frame left off the disk."""
    folder.mkdir(parents=True, exist_ok=True)
    names = [f"frame_{i:03d}.jpg" for i in range(frames)]
    for i, name in enumerate(names):
        if name == skip:
            continue
        texture = np.random.default_rng(0).integers(0, 200, (40, 80, 3))  # sharp, as a photo is: flat reads as blur
        image = (texture + 10 * i).astype(np.uint8)
        cv2.imencode(".jpg", image)[1].tofile(folder / name)  # a non-ASCII folder too
    body = {
        **PROVENANCE,
        "interval_s": 1800,
        "frames": names,
        "tiles": [
            {"label": "A1", "condition": "rye", "run": "sc1", "dish": 1, "box": [0, 0, 40, 40], "seeds": 25},
            {"label": "B1", "condition": "millet", "run": "pg1", "dish": 4, "box": [40, 0, 80, 40], "seeds": 25},
        ],
        "assembled": True,
        "retrospective": True,
        **overrides,
    }
    path = folder / "manifest.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return str(path)


def test_frames_come_every_interval_from_the_manifest(tmp_path):
    frames = list(ImageSequenceSource(write_manifest(tmp_path / "plate")).frames())
    assert [f.t for f in frames] == [0, 1800, 3600]
    assert [f.video_s for f in frames] == [0, 1800, 3600] and {f.file_index for f in frames} == {0}
    assert frames[2].image.shape == (40, 80, 3)


def test_a_missing_frame_is_named_before_any_frame_is_read(tmp_path):
    path = write_manifest(tmp_path / "plate", skip="frame_002.jpg")
    with pytest.raises(ManifestError, match="frame_002.jpg"):
        load_manifest(path)
    with pytest.raises(ManifestError, match="frame_002.jpg"):
        next(ImageSequenceSource(path).frames())


def test_a_frame_that_is_not_an_image_is_named(tmp_path):
    path = write_manifest(tmp_path / "plate")
    (tmp_path / "plate" / "frame_001.jpg").write_text("not a jpeg", encoding="utf-8")
    with pytest.raises(ManifestError, match="frame_001.jpg"):
        load_manifest(path)


def test_a_manifest_keeps_its_tiles_and_provenance(tmp_path):
    manifest = load_manifest(write_manifest(tmp_path / "plate é"))
    assert [t.label for t in manifest.tiles] == ["A1", "B1"] and manifest.tiles[1].box == (40, 0, 80, 40)
    assert manifest.provenance().model_dump() == PROVENANCE | {"assembled": True, "retrospective": True}
