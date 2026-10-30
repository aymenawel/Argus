"""A published image sequence as Argus reads it: the frames in order, the dishes on them (tiles) and where the data
came from. Written by a dataset adapter (argus/datasets/genze.py); third-party files stay in the git-ignored data/.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

from argus.domain import Provenance

# The first bytes of the image files a dataset ships (read directly: OpenCV can't open non-ASCII paths on Windows).
SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"II*\x00", b"MM\x00*", b"BM")


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

    def frame_paths(self) -> list[Path]:
        return [self._root / name for name in self.frames]

    def provenance(self) -> Provenance:
        fields = ("dataset", "doi", "url", "licence", "credit", "assembled", "retrospective")
        return Provenance(**{name: getattr(self, name) for name in fields})


def load_manifest(path: str | Path) -> Manifest:
    """The manifest with every frame checked on disk; ManifestError names the first missing or unreadable one."""
    path = Path(path)
    try:
        manifest = Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as error:
        raise ManifestError(f"manifest not found: {path}") from error
    except (json.JSONDecodeError, ValidationError) as error:
        raise ManifestError(f"{path.name} isn't a valid manifest: {error}") from error
    manifest._root = path.parent
    for frame in manifest.frame_paths():
        if not frame.is_file():
            raise ManifestError(f"{frame.name} is missing (listed in {path.name})")
        with frame.open("rb") as file:
            head = file.read(8)
        if not head.startswith(SIGNATURES):
            raise ManifestError(f"{frame.name} can't be read as an image")
    return manifest
