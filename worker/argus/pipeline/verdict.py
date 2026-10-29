"""The verdict (spec §7.3): the ceiling in code, a Muse Wonder draft and critique, both claim-checked, and the most
cautious allowed choice. Provisional while the run is still going."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from argus.analyze.ceiling import TOO_EARLY, VerdictInputs, ceiling, choose_verdict
from argus.api.events import EventBroker
from argus.claims.checker import check_text_fields, render
from argus.claims.refs import NOTABLE, RefTable, build_refs
from argus.config import Settings
from argus.domain import Plan, Role, Run, RunStatus, Verdict, VerdictDraft, VerdictLevel
from argus.reason import Reasoner, ReasonError, ReasonResult
from argus.reason.prompts import critique_task, load_schema, verdict_task
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import (
    add_model_call,
    add_verdict,
    events_for_run,
    first_locked_plan,
    frames_for_run,
    measurements_for_run,
    notes_for_run,
    reviews_for_run,
    run_spend_usd,
    vessels_for_run,
)

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
        # Locked before the run began, or it isn't a prediction: a plan written with the data in view can't be tested.
        locked=plan is not None and plan.locked_at is not None and plan.locked_at <= run.started_at,
        checkpoint_s=plan.checkpoint_s if plan is not None else None,
        controls=len(controls),
        treatments=len(compared),
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
    times = [f.t for f in frames_for_run(db, run.id)] + [m.t for m in measurements_for_run(db, run.id)]
    return max(times, default=0.0)


def _log(db: Database, run: Run, t: float, result: ReasonResult | None, error: ReasonError | None) -> list[str]:
    calls = []
    if result is not None:
        calls = [*result.failed_calls, result.call]
    elif error is not None:
        calls = [error.call]
    return [add_model_call(db, run.id, t, c).id for c in calls]


TWICE_REJECTED = "The model's drafts failed the claim check twice; this was written by code."
ONLY_TOO_EARLY = "Too early is the only verdict the checks allow, so no model was asked; this was written by code."
VERDICT_WORDS = frozenset(str(level) for level in VerdictLevel)


def _code_draft(allowed: set[VerdictLevel], checks: list, rivals: dict[str, str], *, reason: str) -> dict[str, Any]:
    return {
        "verdict": str(TOO_EARLY if TOO_EARLY in allowed else VerdictLevel.INCONCLUSIVE),
        "explanation": " ".join(c.text for c in checks),
        "rivals": [
            {"name": name, "status": "ruled_out" if state == "resolved" else "open", "reason": "Checked by Argus."}
            for name, state in rivals.items()
        ],
        "what_would_change_it": "",
        "confidence": "low",
        "confidence_reason": reason,
        "refs_used": [],
        "evidence_ids": [],
        "written_by": "code",
    }


def _unknown_verdict(word: object) -> list[str]:
    """A strict schema's enum isn't proof: a word outside it is a rejection, never a crash."""
    return [] if word in VERDICT_WORDS else [f"unknown verdict: {word}"]


async def run_verdict(
    db: Database, broker: EventBroker, settings: Settings, run: Run, *, recipe: Recipe, reasoner: Reasoner
) -> Verdict:
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
    allowed_names = [str(level) for level in VerdictLevel if level in allowed]
    labels = {v.id: v.label for v in vessels_for_run(db, run.id)}
    events = [e for e in events_for_run(db, run.id, t_to=t) if e.kind in NOTABLE]
    notes = notes_for_run(db, run.id, t_to=t)
    prompts = [c.prompt for c in checks]
    call_ids: list[str] = []
    fell_back = False

    draft: dict[str, Any] | None = None
    kept_critique: dict[str, Any] | None = None
    dropped: list[str] = []
    if allowed == {TOO_EARLY}:  # code already knows the only answer: no Wonder call to pay for
        draft = _code_draft(allowed, checks, dict(inputs.rivals), reason=ONLY_TOO_EARLY)
    else:
        rejected: list[str] = []
        for _ in range(2):
            task = verdict_task(
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
                call_ids += _log(db, run, t, None, error)
                rejected = [str(error)]
                continue
            call_ids += _log(db, run, t, result, None)
            fell_back = fell_back or result.fell_back
            rejected = _unknown_verdict(result.data.get("verdict"))
            rejected += check_text_fields(result.data, DRAFT_TEXT, refs)
            rejected += [f"unknown ref: {i}" for i in result.data.get("refs_used", []) if i not in refs]
            if not rejected:
                draft = result.data
                break
        if draft is None:
            draft = _code_draft(allowed, checks, dict(inputs.rivals), reason=TWICE_REJECTED)

        task = critique_task(
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
            call_ids += _log(db, run, t, result, None)
            fell_back = fell_back or result.fell_back
            dropped = _unknown_verdict(result.data.get("revised_verdict"))
            dropped += check_text_fields(result.data, CRITIQUE_TEXT, refs)
            dropped += [f"unknown ref: {i}" for i in result.data.get("refs_used", []) if i not in refs]
            if not dropped:
                kept_critique = result.data
        except ReasonError as error:
            call_ids += _log(db, run, t, None, error)
            dropped = [str(error)]

    revised = VerdictLevel(kept_critique["revised_verdict"]) if kept_critique else None
    final = choose_verdict(allowed, VerdictLevel(draft["verdict"]), revised)
    source = kept_critique or draft
    body = {
        "explanation": render(draft["explanation"], refs),
        "rivals": [{**r, "reason": render(r["reason"], refs)} for r in draft.get("rivals", [])],
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
    verdict = add_verdict(
        db,
        run.id,
        VerdictDraft(
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
        ),
    )
    broker.publish("verdict", {"run_id": run.id, "t": t, "verdict": verdict.model_dump(mode="json")})
    return verdict
