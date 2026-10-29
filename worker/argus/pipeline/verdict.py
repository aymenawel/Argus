"""The verdict (spec §7.3): the ceiling in code, a Muse Wonder draft and critique, both claim-checked, and the most
cautious allowed choice. Provisional while the run is still going."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Literal

from argus.analyze.ceiling import TOO_EARLY, VerdictInputs, ceiling, choose_verdict
from argus.api.events import EventBroker
from argus.claims.checker import check_text_fields, render
from argus.claims.refs import NOTABLE, RefTable, build_refs
from argus.claims.schema import schema_errors
from argus.config import Settings
from argus.domain import Plan, Role, Run, RunMode, RunStatus, Verdict, VerdictDraft, VerdictLevel
from argus.reason import Reasoner, ReasonError, ReasonResult
from argus.reason.prompts import critique_task, load_schema, verdict_task
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import (
    add_model_call,
    add_verdict,
    events_for_run,
    first_locked_plan,
    notes_for_run,
    reviews_for_run,
    run_last_t,
    run_spend_usd,
    vessels_for_run,
)

EXPECTED_VERDICT_CALL_USD = 0.08  # one Wonder call: the first real draft cost $0.063 (D-68)
EXPECTED_VERDICT_USD = 0.15  # a Wonder draft and critique: $0.12 together on the first real run (D-68)
DRAFT_TEXT = ("explanation", "rivals[*].reason", "what_would_change_it", "confidence_reason")
CRITIQUE_TEXT = (
    "confidence_reason",
    "what_would_change_it",
    "findings[*].problem",
    "findings[*].consequence",
    "findings[*].fix",
)


class VerdictRefused(RuntimeError):
    """No verdict can be asked for now: no locked plan, or the spend cap would be passed."""


def rival_states(db: Database, run: Run, rivals: Sequence[str]) -> dict[str, Literal["resolved", "open"]]:
    """Each rival explanation resolved by its check in code, by the researcher (a 'resolve' review), or open."""
    events = events_for_run(db, run.id)
    resolved_by_researcher = {
        r.target_id for r in reviews_for_run(db, run.id) if r.target_kind == "rival" and r.action == "resolve"
    }
    uncorrected = any(
        e.kind == "quality"
        and (
            str(e.detail.get("message", "")).startswith("colour not corrected")
            or "rebaselined" in e.detail.get("flags", [])
        )
        for e in events
    )
    moved = any(e.kind == "camera_moved" for e in events)
    handled = any(e.kind == "intervention" for e in events)
    states: dict[str, Literal["resolved", "open"]] = {}
    for rival in rivals:
        name = rival.lower()
        if rival in resolved_by_researcher:
            states[rival] = "resolved"
        elif "lighting" in name or "exposure" in name:
            states[rival] = "open" if uncorrected else "resolved"
        elif "camera" in name:
            states[rival] = "open" if moved else "resolved"
        elif "handling" in name or "intervention" in name:
            states[rival] = "open" if handled else "resolved"
        else:
            states[rival] = "open"
    return states


def verdict_inputs(db: Database, run: Run, refs: RefTable, *, plan: Plan | None, t: float) -> VerdictInputs:
    """What the ceiling needs, from refs already built for this call (built once, so derived rows aren't doubled)."""
    metric = plan.metric if plan is not None and plan.metric else ""
    data_began = run.source.start_time if run.mode is RunMode.IMPORTED and run.source.start_time else run.started_at
    vessels = vessels_for_run(db, run.id)
    controls = [v for v in vessels if v.role is Role.CONTROL and f"m:{v.label}:{metric}" in refs]
    compared = [
        v
        for v in vessels
        if v.role is Role.TREATMENT
        and (
            plan is None or not plan.treatment or (v.condition is not None and str(v.condition.value) == plan.treatment)
        )
    ]
    effects = {v.label: refs.get(f"diff:{v.label}:{metric}") for v in compared}
    noise = refs.get(f"noise:{metric}")
    min_effect = refs.get("plan:min_effect")
    return VerdictInputs(
        t=t,
        running=run.status is RunStatus.RUNNING,
        # Locked before the data began, or it isn't a prediction: a plan written with the data in view can't be tested.
        # An import's data began when it was recorded, if the researcher said when; the import's start otherwise.
        locked=plan is not None and plan.locked_at is not None and plan.locked_at <= data_began,
        recording_start_known=run.mode is not RunMode.IMPORTED or run.source.start_time is not None,
        checkpoint_s=plan.checkpoint_s if plan is not None else None,
        controls=len(controls),
        treatments=sum(ref is not None for ref in effects.values()),  # measured, not just drawn
        planned=len(compared),
        effects={label: ref for label, ref in effects.items() if ref is not None},
        noise=noise.value if noise is not None else None,
        min_effect=plan.min_effect if plan is not None and plan.min_effect is not None else 0.0,
        direction=plan.direction if plan is not None else None,
        rivals=rival_states(db, run, plan.rivals) if plan is not None else {},
        measured=any(i.startswith("m:") and i.endswith(f":{metric}") for i in refs.ids()),
        noise_display=noise.display if noise is not None else "",
        min_effect_display=min_effect.display if min_effect is not None else "",
        metric=metric,
    )


def allowed_now(db: Database, run: Run, refs: RefTable, *, t: float) -> set[VerdictLevel]:
    """The verdicts a note's hypothesis_status may state at time t (the note writer's ceiling)."""
    plan = first_locked_plan(db, run.experiment_id)
    return ceiling(verdict_inputs(db, run, refs, plan=plan, t=t))[0]


def run_time(db: Database, run: Run) -> float:
    """The run's time now: its newest frame or reading."""
    return run_last_t(db, run.id)


def _log(db: Database, run: Run, t: float, result: ReasonResult | None, error: ReasonError | None) -> list[str]:
    calls = []
    if result is not None:
        calls = [*result.failed_calls, result.call]
    elif error is not None:
        calls = [error.call]
    return [add_model_call(db, run.id, t, c).id for c in calls]


TWICE_REJECTED = "The model's drafts failed the claim check twice; this was written by code."
ONLY_TOO_EARLY = "Too early is the only verdict the checks allow, so no model was asked; this was written by code."
SPEND_CAPPED = "The spend cap was reached before a draft could be written, so this was written by code."


def _rivals(states: dict[str, str], drafted: list[dict], refs: RefTable) -> list[dict[str, str]]:
    """The plan's rivals with code's state (resolved by a check or by the researcher, or open). The model's reason
    is kept only for a rival it named exactly and judged the same way; its paraphrases and inventions are dropped."""
    shown = []
    for name, state in states.items():
        status = "ruled_out" if state == "resolved" else "open"
        agreed = [
            r["reason"]
            for r in drafted
            if r.get("name") == name and (r.get("status") == "ruled_out") == (status == "ruled_out")
        ]
        default = (
            "Ruled out by Argus's checks or by you."
            if status == "ruled_out"
            else "Nothing in this run rules it out yet."
        )
        shown.append({"name": name, "status": status, "reason": render(agreed[0], refs) if agreed else default})
    return shown


def _code_draft(allowed: set[VerdictLevel], checks: list, *, reason: str) -> dict[str, Any]:
    return {
        "verdict": str(TOO_EARLY if TOO_EARLY in allowed else VerdictLevel.INCONCLUSIVE),
        "explanation": " ".join(c.text for c in checks),
        "rivals": [],  # shown from the plan with code's state (_rivals)
        "what_would_change_it": "",
        "confidence": "low",
        "confidence_reason": reason,
        "refs_used": [],
        "evidence_ids": [],
        "written_by": "code",
    }


_writing: set[str] = set()  # runs with a verdict being written: one at a time, so two can't both be paid for
CAPPED = "the spend cap was reached before this call"


def _prepare(
    db: Database, settings: Settings, run: Run, recipe: Recipe
) -> tuple[Plan, float, RefTable, VerdictInputs, set[VerdictLevel], list, dict, list, list]:
    """Everything the verdict reads, and the refs it writes (blocking: run it in a worker thread)."""
    plan = first_locked_plan(db, run.experiment_id)
    if plan is None:
        raise VerdictRefused("no locked plan: lock the plan before the run to get a verdict")
    spent = run_spend_usd(db, run.id)
    if spent + EXPECTED_VERDICT_USD > settings.run_spend_cap_usd:
        raise VerdictRefused(f"the spend cap is reached (${spent:.2f} of ${settings.run_spend_cap_usd:.2f})")
    t = run_time(db, run)
    refs = build_refs(db, run.id, t, recipe=recipe, plan=plan)
    inputs = verdict_inputs(db, run, refs, plan=plan, t=t)
    allowed, checks = ceiling(inputs)
    labels = {v.id: v.label for v in vessels_for_run(db, run.id)}
    events = [e for e in events_for_run(db, run.id, t_to=t) if e.kind in NOTABLE]
    notes = notes_for_run(db, run.id, t_to=t)
    return plan, t, refs, inputs, allowed, checks, labels, events, notes


async def run_verdict(
    db: Database, broker: EventBroker, settings: Settings, run: Run, *, recipe: Recipe, reasoner: Reasoner
) -> Verdict:
    """One verdict per run at a time. The database work runs in worker threads: live capture shares this loop, and a
    long run's refs take seconds to build."""
    if run.id in _writing:
        raise VerdictRefused("a verdict is being written for this run: it arrives in about a minute")
    _writing.add(run.id)
    try:
        return await _write_verdict(db, broker, settings, run, recipe=recipe, reasoner=reasoner)
    finally:
        _writing.discard(run.id)


async def _write_verdict(
    db: Database, broker: EventBroker, settings: Settings, run: Run, *, recipe: Recipe, reasoner: Reasoner
) -> Verdict:
    plan, t, refs, inputs, allowed, checks, labels, events, notes = await asyncio.to_thread(
        _prepare, db, settings, run, recipe
    )
    allowed_names = [str(level) for level in VerdictLevel if level in allowed]
    prompts = [c.prompt for c in checks]
    call_ids: list[str] = []
    fell_back = False

    async def log(result: ReasonResult | None, error: ReasonError | None) -> list[str]:
        return await asyncio.to_thread(_log, db, run, t, result, error)

    async def affordable() -> bool:
        """Each call is checked against the cap again: retries and the critique can push a run past it."""
        spent = await asyncio.to_thread(run_spend_usd, db, run.id)
        return spent + EXPECTED_VERDICT_CALL_USD <= settings.run_spend_cap_usd

    draft: dict[str, Any] | None = None
    kept_critique: dict[str, Any] | None = None
    dropped: list[str] = []
    if allowed == {TOO_EARLY}:  # code already knows the only answer: no Wonder call to pay for
        draft = _code_draft(allowed, checks, reason=ONLY_TOO_EARLY)
    else:
        rejected: list[str] = []
        for _ in range(2):
            if not await affordable():
                rejected = [CAPPED]
                break
            task = await asyncio.to_thread(
                verdict_task,
                recipe,
                plan,
                refs,
                checks=prompts,
                allowed=allowed_names,
                events=events,
                notes=notes,
                experiment_id=run.experiment_id,
                labels=labels,
                rejected=rejected,
            )
            try:
                result = await reasoner(task, tier="deep", schema=load_schema("verdict"), schema_name="ArgusVerdict")
            except ReasonError as error:
                call_ids += await log(None, error)
                rejected = [str(error)]
                continue
            call_ids += await log(result, None)
            fell_back = fell_back or result.fell_back
            rejected = schema_errors(result.data, load_schema("verdict")) or [
                *check_text_fields(result.data, DRAFT_TEXT, refs),
                *(f"unknown ref: {i}" for i in result.data.get("refs_used", []) if i not in refs),
            ]
            if not rejected:
                draft = result.data
                break
        if draft is None:
            reason = SPEND_CAPPED if rejected == [CAPPED] else TWICE_REJECTED
            draft = _code_draft(allowed, checks, reason=reason)

        if not await affordable():
            dropped = [f"skipped: {CAPPED}"]
        else:
            task = await asyncio.to_thread(
                critique_task,
                recipe,
                plan,
                refs,
                checks=prompts,
                allowed=allowed_names,
                draft=draft,
                events=events,
                experiment_id=run.experiment_id,
                labels=labels,
            )
            try:
                result = await reasoner(
                    task, tier="deep", schema=load_schema("verdict_critique"), schema_name="ArgusCritique"
                )
                call_ids += await log(result, None)
                fell_back = fell_back or result.fell_back
                dropped = schema_errors(result.data, load_schema("verdict_critique")) or [
                    *check_text_fields(result.data, CRITIQUE_TEXT, refs),
                    *(f"unknown ref: {i}" for i in result.data.get("refs_used", []) if i not in refs),
                ]
                if not dropped:
                    kept_critique = result.data
            except ReasonError as error:
                call_ids += await log(None, error)
                dropped = [str(error)]

    revised = VerdictLevel(kept_critique["revised_verdict"]) if kept_critique else None
    final = choose_verdict(allowed, VerdictLevel(draft["verdict"]), revised)
    source = kept_critique or draft
    body = {
        "explanation": render(draft["explanation"], refs),
        "rivals": _rivals(dict(inputs.rivals), draft.get("rivals", []), refs),
        "what_would_change_it": render(source.get("what_would_change_it", ""), refs),
        "confidence": source.get("confidence"),
        "confidence_reason": render(source.get("confidence_reason", ""), refs),
        "findings": [
            {k: render(v, refs) if isinstance(v, str) else v for k, v in f.items()}
            for f in (kept_critique or {}).get("findings", [])
        ],
        "written_by": draft.get("written_by", "model"),
        "critique_dropped": dropped,
    }
    used = list(dict.fromkeys([*draft.get("refs_used", []), *(kept_critique or {}).get("refs_used", [])]))
    stored = VerdictDraft(
        t=t,
        provisional=run.status is RunStatus.RUNNING,
        allowed=sorted(allowed, key=lambda level: list(VerdictLevel).index(level)),
        checks=[c.as_dict() for c in checks],
        verdict=final,
        body=body,
        draft=draft,
        critique=kept_critique,
        refs=used,
        model_call_ids=call_ids,
        fell_back=fell_back,
    )
    verdict = await asyncio.to_thread(add_verdict, db, run.id, stored)
    broker.publish("verdict", {"run_id": run.id, "t": t, "verdict": verdict.model_dump(mode="json")})
    return verdict
