"""The highlights reel's chapters (D-85): moments read from stored records, cut to 30–60 s.

A moment is an intervention, a quality flag, a condition's half-way point from its fit, the checkpoint the verdict
judged, or a detected change. Each plays 2 s of run before it and 3 s after, at about two source frames per second
of reel; moments closer than that share a chapter. When they don't fit in 60 s the lowest-ranked go first; when
they fill less than 30 s the chapters slow down. Every caption is stored text (or a fixed label naming a vessel).
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from argus.domain import EventKind
from argus.measure.uncertainty import format_measurement
from argus.media.layout import condition_groups, group_key, note_text
from argus.media.records import RunRecords

Kind = Literal["intervention", "quality", "half_way", "checkpoint", "change"]

TITLE_S, END_S = 3.0, 4.0
PRE_S, POST_S = 2.0, 3.0
MIN_S, MAX_S = 30.0, 60.0
RANK: dict[str, int] = {"intervention": 0, "quality": 0, "half_way": 1, "checkpoint": 2, "change": 3}
KIND_WORDS = {
    "intervention": "Intervention",
    "quality": "Quality flag",
    "half_way": "Half-way",
    "checkpoint": "Checkpoint",
    "change": "Change",
}
VERDICT_WORDS = {
    "SUPPORTED": "Supported",
    "NOT_SUPPORTED": "Not supported",
    "INCONCLUSIVE": "Inconclusive",
    "TOO_EARLY": "Too early",
}
QUALITY = {EventKind.QUALITY: "Quality flag", EventKind.CAMERA_MOVED: "Camera moved"}


@dataclass(frozen=True)
class Moment:
    t: float
    kind: Kind
    caption: str


@dataclass(frozen=True)
class Chapter:
    t_from: float
    t_to: float
    seconds: float  # how long it plays in the reel
    moments: list[Moment] = field(default_factory=list)


def _citing_note(records: RunRecords, event_id: str) -> str | None:
    for note in records.notes:
        if event_id in note.evidence and (text := note_text(note)):
            return text
    return None


def collect_moments(records: RunRecords) -> list[Moment]:
    labels = {v.id: v.label for v in records.vessels}
    moments: list[Moment] = []
    for event in records.events:
        message = event.detail.get("message")
        if event.kind is EventKind.INTERVENTION and message:
            moments.append(Moment(event.t_start, "intervention", str(message)))
        elif event.kind in QUALITY:
            caption = message or _citing_note(records, event.id) or QUALITY[event.kind]
            moments.append(Moment(event.t_start, "quality", str(caption)))
        elif event.kind is EventKind.CHANGE:
            fallback = f"Change detected: {labels[event.vessel_id]}" if event.vessel_id in labels else "Change detected"
            moments.append(Moment(event.t_start, "change", _citing_note(records, event.id) or fallback))

    groups = condition_groups(records.fits["vessels"])
    for key, group in groups.items():
        fitted = [
            v
            for v in records.fits["vessels"]
            if group_key(v) == key and v["fit"] and v["fit"]["ok"] and v["fit"]["reached"] and v["fit"]["half_time_h"]
        ]
        if not fitted:
            continue
        fitted.sort(key=lambda v: v["fit"]["half_time_h"][0])
        vessel = fitted[(len(fitted) - 1) // 2]  # the lower median: a vessel's own fit, no new number
        value, uncertainty = vessel["fit"]["half_time_h"]
        caption = f"Half-way: {vessel['label']} ({group.label}) · {format_measurement(value, uncertainty, 'h')}"
        moments.append(Moment(value * 3600, "half_way", caption))

    if records.verdict is not None:
        explanation = str(records.verdict.body.get("explanation") or "")
        first = explanation.split(". ")[0].rstrip(".")
        caption = f"{first}." if first else f"Verdict: {VERDICT_WORDS[str(records.verdict.verdict)]}"
        moments.append(Moment(records.verdict.t, "checkpoint", caption))
    else:
        checkpoints = [n for n in records.notes if n.level == "checkpoint" and note_text(n)]
        if checkpoints:
            last = max(checkpoints, key=lambda n: n.t)
            moments.append(Moment(last.t, "checkpoint", note_text(last)))
    return sorted(moments, key=lambda x: x.t)


def reel_pace(ts: Sequence[float]) -> float:
    """Run seconds per reel second: about two source frames per second of reel, never faster than real time."""
    steps = [b - a for a, b in zip(ts, ts[1:], strict=False)]
    return max(1.0, 2 * statistics.median(steps)) if steps else 1.0


def _merge(moments: Sequence[Moment], t0: float, t1: float, pace: float) -> list[Chapter]:
    chapters: list[Chapter] = []
    for moment in sorted(moments, key=lambda x: x.t):
        start, end = max(t0, moment.t - PRE_S * pace), min(t1, moment.t + POST_S * pace)
        if chapters and start <= chapters[-1].t_to:
            last = chapters[-1]
            chapters[-1] = Chapter(last.t_from, max(last.t_to, end), 0.0, [*last.moments, moment])
        else:
            chapters.append(Chapter(start, end, 0.0, [moment]))
    return [Chapter(c.t_from, c.t_to, (c.t_to - c.t_from) / pace, c.moments) for c in chapters]


def plan_chapters(moments: Sequence[Moment], t0: float, t1: float, pace: float) -> list[Chapter]:
    if not moments:
        return [Chapter(t0, t1, MIN_S - TITLE_S - END_S, [])]
    kept = sorted(moments, key=lambda x: x.t)
    chapters = _merge(kept, t0, t1, pace)
    while TITLE_S + END_S + sum(c.seconds for c in chapters) > MAX_S and len(kept) > 1:
        # The lowest-ranked moment goes first; among equals, the latest (earlier moments rank higher).
        drop = max(range(len(kept)), key=lambda i: (RANK[kept[i].kind], kept[i].t))
        kept.pop(drop)
        chapters = _merge(kept, t0, t1, pace)
    playing = sum(c.seconds for c in chapters)
    if TITLE_S + END_S + playing < MIN_S and playing > 0:
        stretch = (MIN_S - TITLE_S - END_S) / playing
        chapters = [Chapter(c.t_from, c.t_to, c.seconds * stretch, c.moments) for c in chapters]
    return chapters


def _day(moment) -> str:
    return f"{moment:%b} {moment.day}, {moment.year}"


def title_lines(records: RunRecords) -> list[str]:
    plan = records.plan
    if plan is None or plan.locked_at is None:
        return [records.experiment.title, "No plan was locked for this run"]
    return [
        records.experiment.title,
        f"Hypothesis: {plan.hypothesis}",
        f"Prediction: {plan.prediction}",
        f"Plan locked {_day(plan.locked_at)}",
    ]


def end_lines(records: RunRecords) -> list[str]:
    verdict = records.verdict
    lines = ["No verdict yet"] if verdict is None else [f"Verdict: {VERDICT_WORDS[str(verdict.verdict)]}"]
    if verdict is not None:
        failed = [c for c in verdict.checks if c.get("ok") is False]
        open_ = [c for c in verdict.checks if c.get("ok") is None]
        first = (failed or open_ or [None])[0]
        if first and first.get("text"):
            lines.append(str(first["text"]))
    change = str(records.next_run.body.get("change") or "") if records.next_run is not None else ""
    if change:
        lines.append(f"Next run: {change}")
    return lines
