"""A published image sequence as Argus reads it: the frames in order, the dishes on them (tiles) and where the data
came from. Written by a dataset adapter (argus/datasets/genze.py); third-party files stay in the git-ignored data/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from argus.domain import Provenance

# The first bytes of the image files a dataset ships (read directly: OpenCV can't open non-ASCII paths on Windows).
SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"II*\x00", b"MM\x00*", b"BM")


def _natural(name: str) -> list:
    """frame_2 before frame_10: digits compare as numbers."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


class ManifestError(ValueError):
    """The manifest can't be used; the message names the first file or field at fault."""


class Tile(BaseModel):
    """One dish on the frames: its box (x0, y0, x1, y1) in frame pixels, the condition it belongs to, where it came
    from in the dataset, how many seeds it holds, and the dataset's own per-frame values (for the agreement)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=8)
    condition: str = Field(min_length=1)
    run: str  # the source run, e.g. "sc1"
    dish: int
    box: tuple[int, int, int, int]
    seeds: int = Field(ge=0)
    labels: dict[str, list[float]] = {}  # metric -> one value per frame, from the dataset's annotations


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset: str
    doi: str
    url: str
    licence: str
    credit: str
    interval_s: float = Field(gt=0)
    frames: list[str] = Field(min_length=1)  # file names, next to the manifest
    tiles: list[Tile] = Field(min_length=1)
    assembled: bool = False  # Argus put the frames together (a virtual plate, D-72)
    retrospective: bool = True  # judged after the data existed (D-71)
    dish_diameter_mm: float | None = Field(None, gt=0)  # the published dish size: the dish ruler (D-72)
    sha256: str | None = None  # of the archive the frames came from
    _root: Path = PrivateAttr(default=Path("."))

    @model_validator(mode="after")
    def frames_and_tiles_line_up(self) -> Manifest:
        """Times come from the frames' order, and labels and boxes from the tiles, so each must be exact."""
        seen: set[str] = set()
        for name in self.frames:
            if name in seen:
                raise ValueError(f"{name} is listed twice")
            seen.add(name)
        for before, name in zip(self.frames, self.frames[1:], strict=False):
            if _natural(name) < _natural(before):
                raise ValueError(f"{name} is listed after {before}: frames must be listed in the order they were taken")
        for tile in self.tiles:
            x0, y0, x1, y1 = tile.box
            if not (0 <= x0 < x1 and 0 <= y0 < y1):
                raise ValueError(f"tile {tile.label}'s box {list(tile.box)} isn't a region (x0 < x1, y0 < y1, from 0)")
            for metric, values in tile.labels.items():
                if len(values) != len(self.frames):
                    raise ValueError(
                        f"tile {tile.label}'s {metric} labels have {len(values)} values for {len(self.frames)} frames"
                    )
        return self

    def frame_paths(self) -> list[Path]:
        return [self._root / name for name in self.frames]

    def provenance(self) -> Provenance:
        fields = ("dataset", "doi", "url", "licence", "credit", "assembled", "retrospective")
        return Provenance(**{name: getattr(self, name) for name in fields})


def load_manifest(path: str | Path, *, check_frames: bool = True) -> Manifest:
    """The manifest with every frame checked on disk (unless only its tiles and provenance are wanted);
    ManifestError names the first missing or unreadable one."""
    path = Path(path)
    try:
        manifest = Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as error:
        raise ManifestError(f"manifest not found: {path}") from error
    except (json.JSONDecodeError, ValidationError) as error:
        raise ManifestError(f"{path.name} isn't a valid manifest: {error}") from error
    manifest._root = path.parent
    for frame in manifest.frame_paths() if check_frames else ():
        if not frame.is_file():
            raise ManifestError(f"{frame.name} is missing (listed in {path.name})")
        with frame.open("rb") as file:
            head = file.read(8)
        if not head.startswith(SIGNATURES):
            raise ManifestError(f"{frame.name} can't be read as an image")
    if check_frames:
        first = manifest.frame_paths()[0]
        image = cv2.imdecode(np.fromfile(first, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ManifestError(f"{first.name} can't be read as an image")
        height, width = image.shape[:2]
        for tile in manifest.tiles:
            if tile.box[2] > width or tile.box[3] > height:
                raise ManifestError(f"tile {tile.label}'s box {list(tile.box)} goes outside the {width}×{height} frame")
    return manifest
