"""Make a run's videos into data/<experiment>/<run>/media/ (D-84, D-85)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from argus.config import Settings
from argus.media.draw import Drawer
from argus.media.encode import encode
from argus.media.layout import schedule
from argus.media.moments import (
    END_S,
    KIND_WORDS,
    TITLE_S,
    collect_moments,
    end_lines,
    plan_chapters,
    reel_pace,
    title_lines,
)
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


def make_reel(
    db: Database,
    settings: Settings,
    recipes: Mapping[str, Recipe],
    run_id: str,
    *,
    progress: Progress | None = None,
    fps: int = 30,
) -> Path:
    """30–60 s: a title card with the locked plan, a chapter per moment that mattered, an end card with the verdict."""
    records = load_records(db, settings, recipes, run_id)
    drawer = Drawer(records, settings)
    ts = [f.t for f in records.frames]
    chapters = plan_chapters(collect_moments(records), ts[0], ts[-1], reel_pace(ts))
    title_n, end_n = round(TITLE_S * fps), round(END_S * fps)
    plays = [schedule(ts, c.seconds, fps=fps, t_from=c.t_from, t_to=c.t_to) for c in chapters]
    total = title_n + sum(len(slots) for slots in plays) + end_n

    def frames():
        done = 0

        def tick():
            nonlocal done
            if progress is not None and done % 30 == 0:
                progress(done / total)
            done += 1

        title = drawer.card(title_lines(records))
        for _ in range(title_n):
            tick()
            yield title
        for chapter, slots in zip(chapters, plays, strict=True):
            for slot in slots:
                tick()
                shown = [m for m in chapter.moments if m.t <= slot.t + 1e-6] or chapter.moments[:1]
                if shown:  # the chapter's latest moment so far (its first one before it)
                    yield drawer.run_frame(slot, KIND_WORDS[shown[-1].kind], shown[-1].caption)
                else:  # a run with no moments plays whole, captioned by its notes
                    yield drawer.run_frame(slot)
        end = drawer.card(end_lines(records))
        for _ in range(end_n):
            tick()
            yield end

    out = encode(frames(), records.files.media_path("reel"), fps=fps)
    if progress is not None:
        progress(1.0)
    return out
