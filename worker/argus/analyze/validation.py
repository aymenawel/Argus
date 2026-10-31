"""The validation table for the README (D-86): how well Argus measured, printed by code from stored records.

Each row names the run it comes from. A check with nothing stored behind it for a run reads "not measured yet";
no row is ever filled in by hand. Nothing here calls a model or writes to the database.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from argus.analyze.agreement import agreement
from argus.datasets.manifest import ManifestError, load_manifest
from argus.domain import EventKind, Run, RunStatus
from argus.measure.uncertainty import format_measurement
from argus.media.layout import clock_text
from argus.recipes.model import Recipe
from argus.recipes.resolve import recipe_for
from argus.storage import repos
from argus.storage.db import Database

NOT_MEASURED = "not measured yet"
CHECKS = ("Scale", "Noise floor", "Counting against labels", "Events caught", "Claim checker", "Models")
NOISE_METHODS = {"noise_floor/1": "still period", "noise_floor_wobble/1": "wobble of all readings"}
NOISE_LABEL = re.compile(r"^Noise floor of (\S+)")
REASON = re.compile(r"^(.*?)(?: in \w+)?:")  # "number outside a ref in observation: '25'" → "number outside a ref"


@dataclass(frozen=True)
class Row:
    check: str
    run: str
    result: str


def _dish_diameter(db: Database, run: Run) -> float | None:
    """The dish size the scale was set from: the dataset's manifest, else the experiment's setup."""
    if run.source.manifest:
        try:
            diameter = load_manifest(Path(run.source.manifest)).dish_diameter_mm
        except (ManifestError, OSError, ValueError):
            diameter = None
        if diameter:
            return diameter
    return repos.get_setup(db, run.experiment_id).dish_diameter_mm


def scale(db: Database, run: Run) -> list[str]:
    calibrations = repos.calibrations_for_run(db, run.id)
    if not calibrations:
        return []
    first = calibrations[0]
    value = format_measurement(first.mm_per_px, first.mm_per_px * first.rel_uncertainty, "mm/px")
    if first.card == "dish":
        diameter = _dish_diameter(db, run)
        stated = f" at the dataset's stated {diameter:g} mm diameter" if diameter else ""
        return [f"dish rims{stated} · {value}"]
    if first.card == "ruler":
        return [f"two-click ruler · {value}"]
    return [f"{first.card} card · {value} · print check {first.print_scale * 100:.1f} mm of 100 mm"]


def noise_floor(db: Database, run: Run) -> list[str]:
    latest: dict[str, object] = {}
    for row in sorted(repos.derived_for_run(db, run.id), key=lambda d: d.t):
        match = NOISE_LABEL.match(row.label)
        if row.kind == "noise_floor" and match:
            latest[match.group(1)] = row
    return [
        f"{metric}: {row.value:.2g} {row.unit} ({NOISE_METHODS.get(row.method_version, row.method_version)})"
        for metric, row in latest.items()
    ]


def counting(db: Database, recipe: Recipe, run: Run) -> list[str]:
    found = []
    for metric in recipe.stored_metrics():
        result = agreement(db, run.id, metric)
        if result is None or result.mean_abs_diff is None:
            continue
        rows = repos.measurements_for_run(db, run.id, metric=metric)
        unit = rows[0].unit if rows else ""
        pairs = sum(v.frames for v in result.vessels)  # each vessel's readings that have a label at their time
        vessels = sum(v.frames > 0 for v in result.vessels)
        found.append(
            f"{metric}: mean absolute error {result.mean_abs_diff:.2f} {unit}, exact on {result.exact_share:.0%} "
            f"of {pairs} paired readings across {vessels} {'vessel' if vessels == 1 else 'vessels'}"
        )
    return found


def events_caught(db: Database, run: Run) -> list[str]:
    events = sorted(repos.events_for_run(db, run.id), key=lambda e: e.t_start)
    changes = [e for e in events if e.kind is EventKind.CHANGE]
    found = []
    for event in events:
        if event.kind is not EventKind.INTERVENTION or event.source != "researcher":
            continue  # the quality check logs a hand in view as an intervention too: not one anyone made
        message = event.detail.get("message") or "intervention"
        after = next((c for c in changes if c.t_start >= event.t_start), None)
        caught = f"change after {after.t_start - event.t_start:.0f} s" if after else "no change detected after it"
        found.append(f"'{message}' at {clock_text(event.t_start, None)} → {caught}")
    return found


def claim_checker(db: Database, run: Run) -> list[str]:
    attempts = repos.note_attempts_for_run(db, run.id)
    by_code = sum(n.check_status == "fallback" for n in repos.notes_for_run(db, run.id))
    if not attempts and not by_code:
        return []
    first = sum(a.passed and a.attempt == 1 for a in attempts)
    retried = sum(a.passed and a.attempt > 1 for a in attempts)
    reasons = Counter(
        (m.group(1) if (m := REASON.match(reason)) else reason)
        for a in attempts
        if not a.passed
        for reason in a.reasons
    )
    top = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    failed = sum(not a.passed for a in attempts)
    rejected = f"{failed} answers rejected: " + ", ".join(f"{name} ×{n}" for name, n in top) if top else "none rejected"
    return [f"{first} accepted first try, {retried} after a retry, {by_code} written by code; {rejected}"]


def models(db: Database, run: Run) -> list[str]:
    calls = [c for c in repos.model_calls_for_run(db, run.id) if c.function == "segment"]
    if not calls:
        return []
    ok = sum(c.status == "ok" for c in calls)
    return [f"SAM {ok} of {len(calls)} calls succeeded · spend ${repos.run_spend_usd(db, run.id):.2f}"]


def validation_rows(db: Database, recipes: Mapping[str, Recipe], run_ids: Sequence[str] | None = None) -> list[Row]:
    if run_ids is None:
        runs = [
            run
            for experiment in repos.list_experiments(db)
            for run in repos.runs_for_experiment(db, experiment.id)
            if run.status in (RunStatus.FINISHED, RunStatus.STOPPED)
        ]
        runs.sort(key=lambda r: r.started_at)
    else:
        runs = [run for run_id in run_ids if (run := repos.get_run(db, run_id)) is not None]
    rows = []
    for run in runs:
        experiment = repos.get_experiment(db, run.experiment_id)
        name = f"{experiment.title} ({run.id})"
        recipe = recipe_for(db, recipes, experiment)
        found = {
            "Scale": scale(db, run),
            "Noise floor": noise_floor(db, run),
            "Counting against labels": counting(db, recipe, run),
            "Events caught": events_caught(db, run),
            "Claim checker": claim_checker(db, run),
            "Models": models(db, run),
        }
        for check in CHECKS:
            rows += [Row(check, name, result) for result in found[check] or [NOT_MEASURED]]
    return rows


def render_table(rows: Sequence[Row]) -> str:
    def cell(text: str) -> str:
        return text.replace("|", "\\|")

    lines = ["| Check | Run | Result |", "|---|---|---|"]
    lines += [f"| {cell(r.check)} | {cell(r.run)} | {cell(r.result)} |" for r in rows]
    return "\n".join(lines)
