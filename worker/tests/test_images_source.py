"""Published image sequences as a run source: a manifest names the frames, the dishes (tiles) and where the data
came from; the run keeps that provenance (D-70, D-71)."""

import json
from pathlib import Path

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


def rewrite(path: str, **changes) -> str:
    file = Path(path)
    file.write_text(json.dumps(json.loads(file.read_text(encoding="utf-8")) | changes), encoding="utf-8")
    return path


def tiles_with(**changes) -> list[dict]:
    return [
        {"label": "A1", "condition": "rye", "run": "sc1", "dish": 1, "box": [0, 0, 40, 40], "seeds": 25},
        {"label": "B1", "condition": "millet", "run": "pg1", "dish": 4, "box": [40, 0, 80, 40], "seeds": 25} | changes,
    ]


def test_frames_out_of_order_are_refused_naming_the_first_out_of_place(tmp_path):
    path = rewrite(write_manifest(tmp_path / "p"), frames=["frame_001.jpg", "frame_000.jpg", "frame_002.jpg"])
    with pytest.raises(ManifestError, match="frame_000.jpg"):
        load_manifest(path)


def test_a_frame_listed_twice_is_refused(tmp_path):
    path = rewrite(write_manifest(tmp_path / "p"), frames=["frame_000.jpg", "frame_001.jpg", "frame_001.jpg"])
    with pytest.raises(ManifestError, match="frame_001.jpg"):
        load_manifest(path)


def test_labels_must_have_one_value_per_frame(tmp_path):
    path = rewrite(write_manifest(tmp_path / "p"), tiles=tiles_with(labels={"germinated": [0, 1]}))
    with pytest.raises(ManifestError, match="B1.*germinated"):
        load_manifest(path)


def test_a_box_outside_the_frame_or_inside_out_is_refused(tmp_path):
    outside = rewrite(write_manifest(tmp_path / "a"), tiles=tiles_with(box=[40, 0, 90, 40]))
    with pytest.raises(ManifestError, match="B1"):
        load_manifest(outside)
    inside_out = rewrite(write_manifest(tmp_path / "b"), tiles=tiles_with(box=[80, 0, 40, 40]))
    with pytest.raises(ManifestError, match="B1"):
        load_manifest(inside_out)
