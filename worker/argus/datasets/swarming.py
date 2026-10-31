"""One run of the E. coli swarming recording dataset (Shaw et al. 2026, CC BY 4.0) as frames Argus can import (D-89).

Archive 24-05-08 holds 145 flatbed-scanner scans (3101 × 4375 px TIFFs) of six 100 mm dishes, about one every ten
minutes for 24 hours, each named by the time it was taken (`_YYYYMMDD_HHMMSScc.tif`, cc in hundredths of a second).
Column 1 holds the pLac-gfp control strain, column 2 pLac-fliA; rows 1 to 3 sit on 1, 0.1 and 0 mM IPTG. Argus writes
each scan at half size with one levels stretch, the same on every scan, because SAM can't find the faint swarm on the
dark agar without it; the credit says so. The archive stays in the git-ignored data/ folder; fetch it from the URL.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from argus.datasets.manifest import Manifest, load_manifest

URL = "https://zenodo.org/records/19615229"
DOI = "10.5281/zenodo.19615229"
DATASET = "E. coli swarming time-lapse, run 24-05-08 (Shaw et al. 2026)"
ARCHIVE_MD5 = "dc6d2716b3f1ba26fb6055e9bc7aae2c"  # 24-05-08_tmlps_pLac-gfp-fliA_1-0,1-0mMi.zip, as Zenodo lists it
CREDIT = (
    "Shaw M., Garg S., Kirby J., Schmidgall S., Liguori F., Doshi A., Tu T., Danino T. (2026), Engineered E. coli "
    "swarming for binary and analog input recording, Zenodo; scaled to half size and levels stretched by Argus, the "
    "same on every scan"
)
RUN = "24-05-08"
SCAN_SIZE = (3101, 4375)  # width, height of the published scans
DISH_DIAMETER_MM = 100.0  # "standard Petri dishes (100-mm diameter)", the record's description
HALF_BOX = (
    700  # scan px from a dish's centre to its region's edge: past the outer rim (r ≈ 679), short of the next dish
)
LEVELS = (35.0, 74.0)  # scan levels stretched to black and white: the 1st and 99.5th percentiles of the middle of the
# gfp 1 mM dish on this archive's 24 h scan (agar and the brightest swarm), measured once
SCALE = 0.5
MAX_DRIFT_S = 30.0  # a manifest spaces frames evenly: no scan may sit further than this from its even place
JPEG_QUALITY = 92
SCAN_NAME = re.compile(r"(?:^|/)_(\d{8})_(\d{6})(\d{2})\.tif$")


class SwarmingError(ValueError):
    """The archive can't make these frames; the message names the file or check at fault."""


@dataclass(frozen=True)
class Dish:
    strain: str
    iptg_mm: str  # as the paper writes it
    x: int  # the dish's centre in scan px, from the first scan's rims (the dishes don't move on the scanner)
    y: int

    @property
    def label(self) -> str:
        return f"{self.strain} {self.iptg_mm}"

    @property
    def condition(self) -> str:
        return f"{self.strain}, {self.iptg_mm} mM IPTG"


DISHES: tuple[Dish, ...] = (
    Dish("gfp", "1", 756, 756),
    Dish("fliA", "1", 2292, 750),
    Dish("gfp", "0.1", 852, 2208),
    Dish("fliA", "0.1", 2352, 2160),
    Dish("gfp", "0", 792, 3618),
    Dish("fliA", "0", 2298, 3588),
)


def _digests(path: Path) -> tuple[str, str]:
    """MD5 (what Zenodo publishes) and SHA-256 (what a manifest records), in one read."""
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def _scans(names: list[str]) -> list[tuple[datetime, str]]:
    """Every scan in the archive with the time in its name, oldest first (macOS resource forks left out)."""
    found = []
    for name in names:
        if name.startswith("__MACOSX/") or not (m := SCAN_NAME.search(name)):
            continue
        taken = datetime.strptime(m[1] + m[2], "%Y%m%d%H%M%S").replace(microsecond=int(m[3]) * 10000)
        found.append((taken, name))
    return sorted(found)


def _even_step(scans: list[tuple[datetime, str]]) -> float:
    """The step from the first scan to the last, in seconds; SwarmingError names the scan furthest from its place."""
    times = [(t - scans[0][0]).total_seconds() for t, _ in scans]
    step = times[-1] / (len(times) - 1)
    drift, worst = max((abs(t - i * step), i) for i, t in enumerate(times))
    if drift > MAX_DRIFT_S:
        name = scans[worst][1].rsplit("/", 1)[-1]
        raise SwarmingError(
            f"{name} is {drift:.0f} s from its place on an even {step:.1f} s step (at most {MAX_DRIFT_S:.0f} s): "
            "Argus spaces a dataset's frames evenly"
        )
    return step


def build_frames(
    zip_path: str | Path, out_dir: str | Path, *, expected_md5: str | None = ARCHIVE_MD5, scale: float = SCALE
) -> Manifest:
    """Every scan as a stretched JPEG at `scale` in out_dir, oldest first, and a manifest.json naming the dishes."""
    zip_path, out_dir = Path(zip_path), Path(out_dir)
    md5, sha256 = _digests(zip_path)
    if expected_md5 is not None and md5 != expected_md5:
        raise SwarmingError(f"{zip_path.name}'s MD5 is {md5}, not the published file's {expected_md5}")
    out_dir.mkdir(parents=True, exist_ok=True)
    lo, hi = LEVELS
    with zipfile.ZipFile(zip_path) as archive:
        scans = _scans(archive.namelist())
        if len(scans) < 2:
            raise SwarmingError(
                f"{zip_path.name} holds {len(scans)} scans named _YYYYMMDD_HHMMSScc.tif; 2 or more needed"
            )
        step = _even_step(scans)
        size: tuple[int, int] | None = None
        frame_names: list[str] = []
        for i, (_, name) in enumerate(scans):
            scan = cv2.imdecode(np.frombuffer(archive.read(name), np.uint8), cv2.IMREAD_COLOR)
            short = name.rsplit("/", 1)[-1]
            if scan is None:
                raise SwarmingError(f"{short} can't be read as an image")
            height, width = scan.shape[:2]
            if size is None:
                ratio = SCAN_SIZE[1] / SCAN_SIZE[0]
                if abs(height / width - ratio) > 0.01 * ratio:
                    raise SwarmingError(f"{short} is {width}×{height}, not shaped like the published 3101×4375 scans")
                size = (width, height)
            if (width, height) != size:
                raise SwarmingError(f"{short} is {width}×{height}, not {size[0]}×{size[1]} like the first scan")
            small = cv2.resize(scan, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
            stretched = np.clip((small.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)
            frame = f"scan_{i:03d}.jpg"
            cv2.imencode(".jpg", stretched, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])[1].tofile(out_dir / frame)
            frame_names.append(frame)

    assert size is not None
    f = round(size[0] * scale) / SCAN_SIZE[0]  # scan px to frame px
    tiles = [
        {
            "label": dish.label,
            "condition": dish.condition,
            "run": RUN,
            "dish": k,
            "box": [round(v * f) for v in (dish.x - HALF_BOX, dish.y - HALF_BOX, dish.x + HALF_BOX, dish.y + HALF_BOX)],
            "seeds": 0,
        }
        for k, dish in enumerate(DISHES, start=1)
    ]
    body = {
        "dataset": DATASET,
        "doi": DOI,
        "url": URL,
        "licence": "CC BY 4.0",
        "credit": CREDIT,
        "interval_s": step,
        "frames": frame_names,
        "tiles": tiles,
        "assembled": False,  # the scans as taken, every dish where it sat
        "retrospective": True,
        "dish_diameter_mm": DISH_DIAMETER_MM,
        "sha256": sha256,
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return load_manifest(path)
