"""What a video frame shows at a run time t, and when: which source frame, the clock, the caption, the labels.

Pure functions of stored records, so each can be tested without drawing anything.
"""

from __future__ import annotations

import statistics
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from argus.claims.checker import unlabelled
from argus.domain import Note, Run, RunMode
from argus.plain import metric_words, unit_label

# The app's dark theme (web/styles/tokens.css): a video is dark like a screening room. Checked against the tokens.
PALETTE = {"ground": "#0d0e10", "text": "#f5f7fa", "muted": "#aab0b9", "accent": "#2dd4bf"}

FADE_SHARE = 0.5  # across a long gap, hold the earlier frame for the first half, dissolve in the second


@dataclass(frozen=True)
class Slot:
    """One output frame: run time t, the source frame a at or before it, the next frame b and b's weight."""

    t: float
    a: int
    b: int | None
    w: float


def schedule(
    ts: Sequence[float],
    seconds: float,
    *,
    fps: int = 30,
    t_from: float | None = None,
    t_to: float | None = None,
) -> list[Slot]:
    """Output frames covering run time t_from..t_to (the frames' whole range by default) in `seconds`. Source frames
    sparser than the output are cross-faded, so 95 frames over 47 h play smoothly; dense ones are never blended."""
    if not ts:
        return []
    start = ts[0] if t_from is None else t_from
    end = ts[-1] if t_to is None else t_to
    n = max(1, round(seconds * fps))
    step = (end - start) / (n - 1) if n > 1 else 0.0
    slots = []
    for k in range(n):
        t = end if k == n - 1 and n > 1 else start + step * k
        a = max(0, bisect_right(ts, t + 1e-9) - 1)
        b = a + 1 if a + 1 < len(ts) else None
        w = 0.0
        if b is not None and step > 0 and ts[b] - ts[a] > step:
            frac = (t - ts[a]) / (ts[b] - ts[a])
            w = min(1.0, max(0.0, (frac - FADE_SHARE) / (1 - FADE_SHARE)))
        slots.append(Slot(t, a, b, w))
    return slots


def segments(points: Sequence[tuple[float, float]], gap_factor: float = 3.0) -> list[list[tuple[float, float]]]:
    """Readings split where a step is longer than gap_factor × the median step: a gap in readings stays a gap."""
    if len(points) < 2:
        return [list(points)] if points else []
    steps = [b[0] - a[0] for a, b in zip(points, points[1:], strict=False)]
    limit = gap_factor * statistics.median(steps)
    runs: list[list[tuple[float, float]]] = [[points[0]]]
    for step, point in zip(steps, points[1:], strict=True):
        if step > limit:
            runs.append([])
        runs[-1].append(point)
    return runs


def clock_text(t: float, start_time: datetime | None) -> str:
    """Run time ("23.5 h in", "25 min in"), with the time of day ("· 14:25") when the run's start is known."""
    text = f"{t / 3600:.1f} h in" if t >= 3600 else f"{t / 60:.0f} min in"
    if start_time is not None:
        text += f" · {(start_time + timedelta(seconds=t)):%H:%M}"
    return text


def axis_time(t: float, span: float) -> str:
    """A time on the chart's axis, in the unit the whole run's span reads in: "0 h" … "47 h", "0 min" … "25 min"."""
    if span >= 3600:
        return f"{round(t / 3600, 1):g} h"
    return f"{round(t / 60):g} min"


def note_text(note: Note) -> str:
    """A note as stored: an AI note's observation (it passed the claim checker), a researcher's own words."""
    key = "observation" if note.author == "ai" else "text"
    return unlabelled(str(note.body.get(key) or ""), key)


def caption_at(notes: Sequence[Note], t: float) -> str | None:
    """The text of the latest note at or before t."""
    shown = [n for n in notes if n.t <= t + 1e-6]
    if not shown:
        return None
    return note_text(max(shown, key=lambda n: n.t)) or None


def source_line(run: Run) -> str:
    provenance = run.source.provenance
    if provenance is not None:
        return f"Published data: {provenance.credit} · {provenance.licence}"
    return "Live recording" if run.mode is RunMode.LIVE else "Imported recording"


def words(metric: str) -> str:
    return metric_words(metric)


def metric_title(metric: str, unit: str) -> str:
    """As the Results chart words it (D-95): "Colour change (ΔE)", "Sprouted seeds"."""
    text = words(metric) if unit == "count" else f"{words(metric)} ({unit_label(unit)})"
    return text[:1].upper() + text[1:]


def chart_note(fits: dict) -> str | None:
    """What the chart area says instead of curves when the run has no readings of the main measurement."""
    if any(v["readings"] for v in fits["vessels"]):
        return None
    return f"No readings of {words(fits['metric'])} to draw"


@dataclass(frozen=True)
class Group:
    """A condition's look, as web/lib/chart.ts conditionGroups gives it: controls grey, solid and round."""

    label: str
    control: bool
    dash: tuple[int, int] | None
    marker: str


DASHES: list[tuple[int, int] | None] = [None, (7, 4), (2, 4)]
MARKERS = ["circle", "square", "diamond"]


def condition_value(value: float | str) -> str:
    """A condition's value as the web prints a JSON number: 40.0 reads "40", 2.5 reads "2.5"."""
    return f"{value:g}" if isinstance(value, float) else str(value)


def group_key(vessel: dict) -> str:
    condition = vessel.get("condition")
    return f"{vessel['role']}:{condition['value'] if condition else ''}"


def condition_groups(vessels: Sequence[dict]) -> dict[str, Group]:
    groups: dict[str, Group] = {}
    for vessel in sorted(vessels, key=lambda v: v["role"] != "control"):
        key = group_key(vessel)
        if key in groups:
            continue
        control = vessel["role"] == "control"
        treatments = sum(not g.control for g in groups.values())
        name = "Control" if control else "Test"
        condition = vessel.get("condition")
        groups[key] = Group(
            label=f"{name}: {condition_value(condition['value'])}" if condition else name,
            control=control,
            dash=None if control else DASHES[treatments % len(DASHES)],
            marker="circle" if control else MARKERS[treatments % len(MARKERS)],
        )
    return groups
