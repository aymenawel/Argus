"""The Genze & Grimm germination dataset (CC BY 4.0) as a published plate (D-70, D-72).

The archive holds one 624 × 624 px crop per dish per half hour, with a VOC box on every seed in every frame
(`<sp>_im`: imbibed, `<sp>_el`: germinated). Argus tiles chosen dishes into one frame per time point (a virtual
plate), counts each dish's germinated seeds per frame as the dataset's own label, and writes a manifest naming where
it all came from. Each dataset run held one species, so a plate comparing species mixes runs: the verdict says so.
The archive stays in the git-ignored data/ folder; fetch it from the URL below.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

import cv2
import numpy as np

from argus.datasets.manifest import Manifest, load_manifest

GENZE_SHA256 = "faeb16c61e10150168fc5862020b0ebf45963e80ccfab14aafaec14e85f0090e"  # GermPredDataset.zip, v3
URL = "https://data.mendeley.com/datasets/4wkt6thgp6/3"
DOI = "10.17632/4wkt6thgp6.3"
CREDIT = (
    "Genze N., Bharti R., Grieb M., Schultheiss S.J., Grimm D.G. (2020), Plant Methods 16:157; "
    "cropped and tiled by Argus"
)
INTERVAL_S = 1800.0  # a photo every 30 minutes
DISH_DIAMETER_MM = 85.0
GAP_PX = 2  # between tiles, so no dish's region touches its neighbour's
JPEG_QUALITY = 95

FOLDERS = {"zm": "ZeaMays", "sc": "SecaleCereale", "pg": "PennisetumGlaucum"}
SPECIES = {"zm": "maize", "sc": "rye", "pg": "pearl millet"}


class GenzeError(ValueError):
    """The archive can't make this plate; the message names the file or check at fault."""


@dataclass(frozen=True)
class DishRef:
    species: Literal["zm", "sc", "pg"]
    run: int
    dish: int

    def stem(self, frame: int) -> str:
        return f"{self.species}{self.run}_{self.dish}_img{frame:03d}"

    def path(self, kind: Literal["img", "true_ann"], frame: int) -> str:
        suffix = "jpg" if kind == "img" else "xml"
        return f"GermPredDataset/{FOLDERS[self.species]}/{kind}/{self.stem(frame)}.{suffix}"


# Rye against pearl millet: three dishes each, from two runs per species (so the run-to-run rival is real).
DEFAULT_PLATE: tuple[DishRef, ...] = (
    DishRef("sc", 1, 1),
    DishRef("sc", 1, 2),
    DishRef("sc", 2, 1),
    DishRef("pg", 1, 1),
    DishRef("pg", 1, 2),
    DishRef("pg", 2, 1),
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_numbers(names: Sequence[str], dish: DishRef) -> set[int]:
    pattern = re.compile(rf"/img/{dish.species}{dish.run}_{dish.dish}_img(\d+)\.jpg$")
    return {int(m[1]) for name in names if (m := pattern.search(name))}


def _boxes(archive: zipfile.ZipFile, dish: DishRef, frame: int) -> list[str]:
    """The label of every seed box in one frame (a checksummed archive from the dataset's authors)."""
    try:
        root = ElementTree.fromstring(archive.read(dish.path("true_ann", frame)))
    except KeyError as error:
        raise GenzeError(f"{dish.stem(frame)}.xml is missing from the archive") from error
    return [(obj.findtext("name") or "").strip() for obj in root.iter("object")]


def build_plate(
    zip_path: str | Path,
    out_dir: str | Path,
    *,
    dishes: Sequence[DishRef] = DEFAULT_PLATE,
    columns: int = 3,
    expected_sha256: str | None = GENZE_SHA256,
) -> Manifest:
    """Tile `dishes` into one frame per time point, `columns` across, in out_dir with a manifest.json; every dish
    must have every frame up to the shortest dish's last."""
    zip_path, out_dir = Path(zip_path), Path(out_dir)
    digest = sha256_of(zip_path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise GenzeError(f"{zip_path.name}'s SHA-256 is {digest}, not the published file's {expected_sha256}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        available = {dish: _frame_numbers(names, dish) for dish in dishes}
        empty = [d.stem(1).rsplit("_img", 1)[0] for d, frames in available.items() if not frames]
        if empty:
            raise GenzeError(f"no frames in the archive for {', '.join(empty)}")
        count = min(max(frames) for frames in available.values())
        for dish, frames in available.items():
            missing = next((i for i in range(1, count + 1) if i not in frames), None)
            if missing is not None:
                raise GenzeError(f"{dish.stem(missing)}.jpg is missing from the archive")

        across = min(columns, len(dishes))
        rows = math.ceil(len(dishes) / across)
        size: tuple[int, int] | None = None
        frame_names: list[str] = []
        germinated: dict[DishRef, list[int]] = {dish: [] for dish in dishes}
        seeds: dict[DishRef, int] = {}
        for i in range(1, count + 1):
            crops = []
            for dish in dishes:
                crop = cv2.imdecode(np.frombuffer(archive.read(dish.path("img", i)), np.uint8), cv2.IMREAD_COLOR)
                if crop is None:
                    raise GenzeError(f"{dish.stem(i)}.jpg can't be read as an image")
                if size is None:
                    size = crop.shape[:2]
                if crop.shape[:2] != size:
                    raise GenzeError(f"{dish.stem(i)}.jpg is {crop.shape[1]}×{crop.shape[0]}, not {size[1]}×{size[0]}")
                crops.append(crop)
                labels = _boxes(archive, dish, i)
                germinated[dish].append(sum(label.endswith("_el") for label in labels))
                seeds.setdefault(dish, len(labels))
            assert size is not None
            h, w = size
            plate = np.zeros((rows * h + (rows - 1) * GAP_PX, across * w + (across - 1) * GAP_PX, 3), np.uint8)
            for k, crop in enumerate(crops):
                x0, y0 = (k % across) * (w + GAP_PX), (k // across) * (h + GAP_PX)
                plate[y0 : y0 + h, x0 : x0 + w] = crop
            name = f"plate_{i:03d}.jpg"
            cv2.imencode(".jpg", plate, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])[1].tofile(out_dir / name)
            frame_names.append(name)

    assert size is not None
    h, w = size
    tiles = []
    for k, dish in enumerate(dishes):
        x0, y0 = (k % across) * (w + GAP_PX), (k // across) * (h + GAP_PX)
        tiles.append(
            {
                "label": f"{dish.species}{dish.run}-{dish.dish}",
                "condition": SPECIES[dish.species],
                "run": f"{dish.species}{dish.run}",
                "dish": dish.dish,
                "box": [x0, y0, x0 + w, y0 + h],
                "seeds": seeds[dish],
                "labels": {"germinated": germinated[dish]},
            }
        )
    body = {
        "dataset": "Genze & Grimm germination dataset",
        "doi": DOI,
        "url": URL,
        "licence": "CC BY 4.0",
        "credit": CREDIT,
        "interval_s": INTERVAL_S,
        "frames": frame_names,
        "tiles": tiles,
        "assembled": True,
        "retrospective": True,
        "dish_diameter_mm": DISH_DIAMETER_MM,
        "sha256": digest,
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return load_manifest(path)
