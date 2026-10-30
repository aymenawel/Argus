"""The next run (D-80): code's numbers as refs, Muse Wonder's reasons through the claim checker, stored append-only.
Two rejected answers (or no model, or the spend cap) and code writes the suggestion from its own numbers. Only for a
run that has ended; Argus suggests and never starts a run or moves hardware."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from argus.analyze.next_run import NextRunNumbers, next_run_numbers
from argus.claims.checker import check_text_fields, render
from argus.claims.refs import Ref, RefTable, build_refs
from argus.claims.schema import schema_errors
from argus.config import Settings
from argus.domain import NextRun, NextRunDraft, Plan, Run, RunStatus
from argus.reason import Reasoner, ReasonError, ReasonResult
from argus.reason.prompts import load_schema, next_run_task
from argus.recipes.draft import safety_screen
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import (
    add_model_call,
    add_next_run,
    first_locked_plan,
    latest_verdict,
    run_last_t,
    run_spend_usd,
    vessels_for_run,
)

EXPECTED_NEXT_RUN_CALL_USD = 0.08  # one Wonder call, like a verdict draft (D-68)
TEXT = ("why", "change", "watch_for")
TWICE_REJECTED = "The model's answers failed the claim check twice; this was written by code."
NO_MODEL = "Reasoning is off (no MODEL_API_KEY), so this was written by code."
SPEND_CAPPED = "The spend cap was reached, so this was written by code."


class NextRunRefused(RuntimeError):
    """No next run can be suggested now: the run is still going, or one is being written."""


def _hours(h: float) -> str:
    return f"{h:.0f} h" if h >= 10 else f"{h:.1f} h"


def _next_refs(numbers: NextRunNumbers, factor_unit: str) -> dict[str, Ref]:
    """The numbers as refs the model may cite: next:replicates, next:hours, next:level:<i>."""
    refs: dict[str, Ref] = {}
    if numbers.replicates is not None:
        n = numbers.replicates
        refs["next:replicates"] = Ref(
            "next:replicates", "vessels per condition next run", n, 0.0, "vessels", f"{n} vessels", "next", None, None
        )
    if numbers.hours is not None:
        h = numbers.hours
        refs["next:hours"] = Ref("next:hours", "next run's length", h, 0.0, "h", _hours(h), "next", None, None)
    for i, level in enumerate(numbers.levels, start=1):
        display = f"{level:g} {factor_unit}".strip()
        refs[f"next:level:{i}"] = Ref(
            f"next:level:{i}", f"level {i} to try", level, 0.0, factor_unit, display, "next", None, None
        )
    return refs


def _prepare(db: Database, run: Run, recipe: Recipe) -> dict[str, Any]:
    """Everything the suggestion reads, and the refs it writes (blocking: run it in a worker thread)."""
    plan = first_locked_plan(db, run.experiment_id)
    t = run_last_t(db, run.id)
    numbers = next_run_numbers(db, run, recipe, plan)
    vessels = vessels_for_run(db, run.id)
    conditions = [v.condition for v in vessels if v.condition is not None]
    factor_unit = next((c.unit for c in conditions if c.unit), "")
    base = build_refs(db, run.id, t, recipe=recipe, plan=plan)
    refs = RefTable({**base.refs, **_next_refs(numbers, factor_unit)})
    verdict = latest_verdict(db, run.id)
    words = " ".join(dict.fromkeys(f"{c.factor} {c.value}" for c in conditions))
    return {
        "plan": plan,
        "t": t,
        "numbers": numbers,
        "refs": refs,
        "verdict": str(verdict.verdict) if verdict else "none yet",
        "checks": [c["text"] for c in verdict.checks] if verdict else [],
        "open_rivals": [r["name"] for r in verdict.body.get("rivals", []) if r.get("status") == "open"]
        if verdict
        else [],
        "safety": safety_screen(words, []),
    }


def _pairs(numbers: NextRunNumbers, refs: RefTable) -> list[tuple[str, str]]:
    """Each number by its ref id (or its name when unknown), with code's reason."""
    pairs = [
        ("next:replicates" if "next:replicates" in refs else "replicates (unknown)", numbers.replicates_reason),
        ("next:hours" if "next:hours" in refs else "run length (unknown)", numbers.hours_reason),
    ]
    if numbers.levels:
        pairs += [(f"next:level:{i}", numbers.levels_reason) for i in range(1, len(numbers.levels) + 1)]
    else:
        pairs.append(("levels (none)", numbers.levels_reason))
    return pairs


def _code_body(numbers: NextRunNumbers, refs: RefTable, reason: str) -> dict[str, str]:
    """The suggestion from code's own numbers, when no checked model answer is available."""
    replicates = f"{numbers.replicates} vessels per condition" if numbers.replicates is not None else "Replicates"
    hours_ref = refs.get("next:hours")
    hours = f"Run for {hours_ref.display}" if hours_ref is not None else "Run length"
    shown = (refs.get(f"next:level:{i}") for i in range(1, len(numbers.levels) + 1))
    levels = ", ".join(r.display for r in shown if r is not None)
    parts = [
        f"{replicates}: {numbers.replicates_reason}.",
        f"{hours}: {numbers.hours_reason}.",
        f"Levels to try: {levels}; {numbers.levels_reason}." if levels else f"Levels: {numbers.levels_reason}.",
    ]
    return {"why": " ".join(parts), "change": "", "watch_for": "", "written_by": "code", "code_reason": reason}


_writing: set[str] = set()  # runs with a suggestion being written: one at a time, so two can't both be paid for


async def suggest_next_run(
    db: Database, run: Run, recipe: Recipe, reasoner: Reasoner | None, settings: Settings
) -> NextRun:
    if run.status is RunStatus.RUNNING:
        raise NextRunRefused("the run is still going: the next run is suggested once it has ended")
    if run.id in _writing:
        raise NextRunRefused("a next run is being suggested for this run: it arrives in about a minute")
    _writing.add(run.id)
    try:
        return await _suggest(db, run, recipe, reasoner, settings)
    finally:
        _writing.discard(run.id)


def _log(db: Database, run: Run, t: float, result: ReasonResult | None, error: ReasonError | None) -> list[str]:
    calls = [*result.failed_calls, result.call] if result is not None else [error.call] if error is not None else []
    return [add_model_call(db, run.id, t, c).id for c in calls]


async def _suggest(db: Database, run: Run, recipe: Recipe, reasoner: Reasoner | None, settings: Settings) -> NextRun:
    ctx = await asyncio.to_thread(_prepare, db, run, recipe)
    plan: Plan | None = ctx["plan"]
    t: float = ctx["t"]
    numbers: NextRunNumbers = ctx["numbers"]
    refs: RefTable = ctx["refs"]
    schema = load_schema("next_run")
    call_ids: list[str] = []
    fell_back = False
    kept: dict[str, Any] | None = None
    reason = NO_MODEL
    rejected: list[str] = []
    for _ in range(2 if reasoner is not None else 0):
        spent = await asyncio.to_thread(run_spend_usd, db, run.id)
        if spent + EXPECTED_NEXT_RUN_CALL_USD > settings.run_spend_cap_usd:
            reason = SPEND_CAPPED
            break
        reason = TWICE_REJECTED
        task = next_run_task(
            recipe,
            plan,
            refs,
            numbers=_pairs(numbers, refs),
            verdict=ctx["verdict"],
            checks=ctx["checks"],
            open_rivals=ctx["open_rivals"],
            experiment_id=run.experiment_id,
            rejected=rejected,
        )
        try:
            result = await reasoner(task, tier="deep", schema=schema, schema_name="ArgusNextRun")  # type: ignore[misc]
        except ReasonError as error:
            call_ids += await asyncio.to_thread(_log, db, run, t, None, error)
            rejected = [str(error)]
            continue
        call_ids += await asyncio.to_thread(_log, db, run, t, result, None)
        fell_back = fell_back or result.fell_back
        rejected = schema_errors(result.data, schema) or [
            *check_text_fields(result.data, TEXT, refs),
            *(f"unknown ref: {i}" for i in result.data.get("refs_used", []) if i not in refs),
        ]
        if not rejected:
            kept = result.data
            break

    if kept is not None:
        body: dict[str, Any] = {key: render(kept[key], refs) for key in TEXT} | {"written_by": "model"}
        used = [i for i in kept.get("refs_used", []) if i in refs]
    else:
        body = _code_body(numbers, refs, reason)
        used = [i for i in ("next:replicates", "next:hours") if i in refs]
    body["safety"] = ctx["safety"]
    draft = NextRunDraft(
        t=t,
        numbers=asdict(numbers),
        body=body,
        refs=list(dict.fromkeys(used)),
        model_call_ids=call_ids,
        fell_back=fell_back,
    )
    return await asyncio.to_thread(add_next_run, db, run.id, draft)
