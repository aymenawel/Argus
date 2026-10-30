"""The Genze & Grimm germination dataset as a published plate: per-dish crops tiled into one frame per time point,
each seed's human label counted per frame (D-70, D-72). Tested on a small synthetic zip in Genze's layout."""

import hashlib
import json
import zipfile

import cv2
import numpy as np
import pytest

from argus import cli
from argus.datasets.genze import DishRef, GenzeError, build_plate
from argus.datasets.manifest import load_manifest

FOLDERS = {"sc": "SecaleCereale", "pg": "PennisetumGlaucum", "zm": "ZeaMays"}


def voc(name: str, boxes: list[str]) -> str:
    objects = "".join(
        f"<object><name>{label}</name><bndbox><xmin>{i}</xmin><ymin>1</ymin><xmax>{i + 9}</xmax><ymax>9</ymax>"
        "</bndbox></object>"
        for i, label in enumerate(boxes)
    )
    return f"<annotation><filename>{name}.jpg</filename>{objects}</annotation>"


def make_zip(path, *, frames=3, skip: str | None = None) -> str:
    """Two dishes, rye run 1 dish 1 (germinating 0, 1, 2 of 3 seeds) and millet run 2 dish 4 (0, 0, 1 of 2)."""
    germinated = {("sc", 1, 1): ([0, 1, 2], 3), ("pg", 2, 4): ([0, 0, 1], 2)}
    with zipfile.ZipFile(path, "w") as z:
        for (sp, run, dish), (counts, seeds) in germinated.items():
            for i in range(frames):
                name = f"{sp}{run}_{dish}_img{i + 1:03d}"
                if name == skip:
                    continue
                image = np.full((624, 624, 3), 60 + 20 * i, np.uint8)
                z.writestr(f"GermPredDataset/{FOLDERS[sp]}/img/{name}.jpg", cv2.imencode(".jpg", image)[1].tobytes())
                boxes = [f"{sp}_el"] * counts[i] + [f"{sp}_im"] * (seeds - counts[i])
                z.writestr(f"GermPredDataset/{FOLDERS[sp]}/true_ann/{name}.xml", voc(name, boxes))
    return hashlib.sha256(path.read_bytes()).hexdigest()


DISHES = [DishRef("sc", 1, 1), DishRef("pg", 2, 4)]


def test_two_dishes_become_a_plate_with_their_labels(tmp_path):
    archive = tmp_path / "GermPredDataset.zip"
    digest = make_zip(archive)
    manifest = build_plate(archive, tmp_path / "plate", dishes=DISHES, expected_sha256=digest)
    assert [t.box for t in manifest.tiles] == [(0, 0, 624, 624), (626, 0, 1250, 624)]
    rye, millet = manifest.tiles
    assert (rye.condition, rye.run, rye.dish, rye.seeds) == ("rye", "sc1", 1, 3)
    assert (millet.condition, millet.run, millet.seeds) == ("pearl millet", "pg2", 2)
    assert rye.labels["germinated"] == [0, 1, 2] and millet.labels["germinated"] == [0, 0, 1]
    assert manifest.interval_s == 1800 and len(manifest.frames) == 3 and manifest.sha256 == digest
    assert manifest.credit.endswith("cropped and tiled by Argus") and manifest.assembled and manifest.retrospective
    assert manifest.dish_diameter_mm == 85.0
    loaded = load_manifest(tmp_path / "plate" / "manifest.json")  # every frame on disk, at the plate's size
    frame = cv2.imdecode(np.fromfile(loaded.frame_paths()[0], np.uint8), cv2.IMREAD_COLOR)
    assert frame.shape[:2] == (624, 1250)


def test_a_dish_missing_a_frame_is_refused_by_name(tmp_path):
    archive = tmp_path / "GermPredDataset.zip"
    digest = make_zip(archive, skip="pg2_4_img002")
    with pytest.raises(GenzeError, match="pg2_4_img002"):
        build_plate(archive, tmp_path / "plate", dishes=DISHES, expected_sha256=digest)


def test_a_changed_zip_fails_the_checksum(tmp_path):
    archive = tmp_path / "GermPredDataset.zip"
    make_zip(archive)
    with pytest.raises(GenzeError, match="SHA-256"):
        build_plate(archive, tmp_path / "plate", dishes=DISHES, expected_sha256="0" * 64)


def test_the_cli_builds_the_plate(tmp_path, monkeypatch, capsys):
    archive = tmp_path / "GermPredDataset.zip"
    digest = make_zip(archive)
    monkeypatch.setattr("argus.datasets.genze.GENZE_SHA256", digest)
    monkeypatch.setattr("argus.datasets.genze.DEFAULT_PLATE", tuple(DISHES))
    assert cli.main(["dataset", "genze", "--zip", str(archive), "--out", str(tmp_path / "plate")]) == 0
    manifest = json.loads((tmp_path / "plate" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["tiles"]) == 2 and "manifest.json" in capsys.readouterr().out
