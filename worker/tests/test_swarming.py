"""The E. coli swarming dataset (Shaw et al. 2026) as frames Argus can import: six dishes on a flatbed scanner, one
scan about every ten minutes, scaled to half size with one fixed levels stretch (D-89). Tested on a small synthetic
zip in the archive's layout, its scans a fifth of the real size."""

import hashlib
import json
import zipfile
from datetime import datetime, timedelta
from itertools import combinations

import cv2
import numpy as np
import pytest

from argus import cli
from argus.datasets.manifest import load_manifest
from argus.datasets.swarming import DISHES, SCAN_SIZE, SwarmingError, build_frames

FOLDER = "24-05-08_tmlps_gfp-fliA_1-0,1-0mMi"
START = datetime(2024, 5, 8, 14, 7, 15, 170000)
WIDTH, HEIGHT = 620, 875  # the real scans are 3101 x 4375


def scan_name(t: datetime) -> str:
    return f"{FOLDER}/_{t:%Y%m%d}_{t:%H%M%S}{t.microsecond // 10000:02d}.tif"


def make_zip(path, *, gaps=(601.5, 601.5), size=(WIDTH, HEIGHT), odd_size_at: int | None = None) -> str:
    """Scans of agar at level 35 with a swarm at level 74 in every dish, plus the files the real archive also holds."""
    f = size[0] / SCAN_SIZE[0]
    times = [START]
    for gap in gaps:
        times.append(times[-1] + timedelta(seconds=gap))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{FOLDER}/24-05-08_tmlps_timestamps.xlsx", b"PK not read")
        z.writestr(f"{FOLDER}/24-05-08_tmlps_labeled-frame.png", b"\x89PNG not read")
        z.writestr(f"__MACOSX/{FOLDER}/._x.tif", b"resource fork")
        for i, t in enumerate(reversed(times)):  # stored out of order: the times decide the order
            w, h = (size[0] + 10, size[1]) if i == odd_size_at else size
            scan = np.full((h, w, 3), 35, np.uint8)
            for dish in DISHES:
                cv2.circle(scan, (round(dish.x * f), round(dish.y * f)), 10, (74, 74, 74), -1)
            z.writestr(scan_name(t), cv2.imencode(".tif", scan)[1].tobytes())
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_scans_become_half_size_frames_with_six_dishes(tmp_path):
    archive = tmp_path / "swarming.zip"
    md5 = make_zip(archive)
    manifest = build_frames(archive, tmp_path / "frames", expected_md5=md5)
    assert manifest.frames == ["scan_000.jpg", "scan_001.jpg", "scan_002.jpg"]
    assert manifest.interval_s == pytest.approx(601.5)
    labels = [(t.label, t.condition, t.dish) for t in manifest.tiles]
    assert labels == [
        ("gfp 1", "gfp, 1 mM IPTG", 1),
        ("fliA 1", "fliA, 1 mM IPTG", 2),
        ("gfp 0.1", "gfp, 0.1 mM IPTG", 3),
        ("fliA 0.1", "fliA, 0.1 mM IPTG", 4),
        ("gfp 0", "gfp, 0 mM IPTG", 5),
        ("fliA 0", "fliA, 0 mM IPTG", 6),
    ]
    assert manifest.dish_diameter_mm == 100.0 and not manifest.assembled and manifest.retrospective
    assert manifest.licence == "CC BY 4.0" and manifest.doi == "10.5281/zenodo.19615229"
    assert "levels stretched by Argus" in manifest.credit
    assert manifest.sha256 == hashlib.sha256(archive.read_bytes()).hexdigest()
    loaded = load_manifest(tmp_path / "frames" / "manifest.json")  # every frame on disk, every box inside it
    frame = cv2.imdecode(np.fromfile(loaded.frame_paths()[0], np.uint8), cv2.IMREAD_COLOR)
    assert frame.shape[:2] == (round(HEIGHT / 2), WIDTH // 2)
    f = (WIDTH // 2) / SCAN_SIZE[0]
    for tile, dish in zip(manifest.tiles, DISHES, strict=True):
        x0, y0, x1, y1 = tile.box
        assert abs((x0 + x1) / 2 - dish.x * f) <= 1 and abs((y0 + y1) / 2 - dish.y * f) <= 1  # centred on the dish
        assert frame[round(dish.y * f), round(dish.x * f)].min() >= 245  # the swarm, stretched to white
        assert frame[y0 + 2, x0 + 2].max() <= 10  # the agar, stretched to black
    for a, b in combinations(manifest.tiles, 2):  # no dish's region reaches into another's
        boxes_overlap = a.box[0] < b.box[2] and b.box[0] < a.box[2] and a.box[1] < b.box[3] and b.box[1] < a.box[3]
        assert not boxes_overlap, (a.label, b.label)


def test_unevenly_spaced_scans_are_refused_by_name(tmp_path):
    """A manifest spaces its frames evenly from the first to the last, so a scan far from its even place would be
    measured at the wrong time: the one farthest from it is named."""
    archive = tmp_path / "swarming.zip"
    md5 = make_zip(archive, gaps=(601.5, 700.0))  # an even step of 650.75 s puts the middle scan 49 s early
    off = scan_name(START + timedelta(seconds=601.5)).rsplit("/", 1)[1]
    with pytest.raises(SwarmingError, match=off):
        build_frames(archive, tmp_path / "frames", expected_md5=md5)


def test_a_scan_of_another_size_is_refused_by_name(tmp_path):
    archive = tmp_path / "swarming.zip"
    md5 = make_zip(archive, odd_size_at=0)  # the last scan, stored first
    last = scan_name(START + timedelta(seconds=1203)).rsplit("/", 1)[1]
    with pytest.raises(SwarmingError, match=last):
        build_frames(archive, tmp_path / "frames", expected_md5=md5)


def test_a_changed_archive_fails_the_checksum(tmp_path):
    archive = tmp_path / "swarming.zip"
    make_zip(archive)
    with pytest.raises(SwarmingError, match="MD5"):
        build_frames(archive, tmp_path / "frames", expected_md5="0" * 32)


def test_the_cli_builds_the_frames(tmp_path, monkeypatch, capsys):
    archive = tmp_path / "swarming.zip"
    monkeypatch.setattr("argus.datasets.swarming.ARCHIVE_MD5", make_zip(archive))
    assert cli.main(["dataset", "swarming", "--zip", str(archive), "--out", str(tmp_path / "frames")]) == 0
    manifest = json.loads((tmp_path / "frames" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["tiles"]) == 6 and "manifest.json" in capsys.readouterr().out
