"""Make a run's videos into data/<experiment>/<run>/media/ (D-84, D-85)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from argus.config import Settings
from argus.media.draw import Drawer
from argus.media.encode import encode
from argus.media.layout import schedule
from argus.media.records import load_records
from argus.recipes.model import Recipe
from argus.storage.db import Database

Progress = Callable[[float], None]


def make_timelapse(
    db: Database,
    settings: Settings,
    recipes: Mapping[str, Recipe],
    run_id: str,
    *,
    seconds: float = 20.0,
    progress: Progress | None = None,
) -> Path:
    """The whole run in `seconds`, its curves drawn up to each moment."""
    records = load_records(db, settings, recipes, run_id)
    drawer = Drawer(records, settings)
    slots = schedule([f.t for f in records.frames], seconds)

    def frames():
        for k, slot in enumerate(slots):
            if progress is not None and k % 30 == 0:
                progress(k / len(slots))
            yield drawer.run_frame(slot)

    out = encode(frames(), records.files.media_path("timelapse"))
    if progress is not None:
        progress(1.0)
    return out
