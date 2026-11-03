"""Ask Argus (D-97): a researcher's question about the moment at t, answered from the run's own records.

The answer sees what a note would see at t (the refs, events, recent notes, the plan, the verdicts allowed) plus the
run's last questions and the picture at that moment. Every number in it is a ref the claim checker accepts; twice
rejected, or a failed call, and code writes the answer from the readings instead.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

import cv2

from argus.claims.checker import check_text_fields, render, unlabelled
from argus.claims.refs import NOTABLE, RefTable, build_refs, format_run_time
from argus.claims.schema import schema_errors
from argus.config import Settings
from argus.domain import ChatMessage, ChatMessageDraft, Frame, Run, VerdictLevel
from argus.pipeline.verdict import allowed_now
from argus.reason import Reasoner, ReasonError
from argus.reason.prompts import chat_task, load_schema, snapshot_jpeg
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database

log = logging.getLogger(__name__)

EXPECTED_CHAT_USD = 0.01  # one routine answer with one picture (KB 05: under a cent)
HISTORY = 6  # the run's last questions and answers the model sees


class ChatRefused(Exception):
    """A question Argus won't send to a model: the run's spending limit."""


def clamp_t(frames: Sequence[Frame], t: float) -> float:
    """The moment asked about, inside what was analysed: 0 before the first analysed picture."""
    analysed = [f.t for f in frames if f.analyzed]
    return min(max(t, 0.0), max(analysed)) if analysed else 0.0


def _picture(settings: Settings, frames: Sequence[Frame], t: float) -> tuple[bytes, ...]:
    """The newest analysed picture at or before t, shrunk as notes send it; none when there is none."""
    shown = [f for f in frames if f.analyzed and f.t <= t + 1e-6]
    if not shown:
        return ()
    image = cv2.imread(str(settings.data_dir / max(shown, key=lambda f: f.t).path))
    return () if image is None else (snapshot_jpeg(image, settings.snapshot_px),)


def fallback_answer(refs: RefTable, when: str) -> str:
    """Code's own answer: what was measured at that moment, no model words."""
    readings = [r for i in refs.ids() if i.startswith("m:") and (r := refs.get(i)) is not None]
    if not readings:
        return "Argus hasn't measured anything yet at this moment."
    listed = "; ".join(f"{r.label}: {r.display}" for r in readings)
    return f"I couldn't answer that without guessing a number. Here is what Argus measured at {when}: {listed}."


def _problems(data: dict, refs: RefTable) -> list[str]:
    reasons = schema_errors(data, load_schema("chat_answer"))
    if reasons:
        return reasons  # a wrong shape is a reason to retry, never a crash in the checks after it
    reasons = check_text_fields(data, ["answer"], refs)
    return reasons + [f"unknown ref in refs_used: {i}" for i in data["refs_used"] if i not in refs]


async def ask_chat(
    db: Database, settings: Settings, run: Run, recipe: Recipe, reasoner: Reasoner, t: float, question: str
) -> ChatMessage:
    spent = await asyncio.to_thread(repos.run_spend_usd, db, run.id)
    if spent + EXPECTED_CHAT_USD > settings.run_spend_cap_usd:
        raise ChatRefused("This run has reached its spending limit")
    frames = await asyncio.to_thread(repos.frames_for_run, db, run.id)
    t = clamp_t(frames, t)
    span = max((f.t for f in frames), default=t)
    when = format_run_time(t, span)
    plan = await asyncio.to_thread(repos.first_locked_plan, db, run.experiment_id)
    refs = await asyncio.to_thread(build_refs, db, run.id, t, recipe=recipe, plan=plan)
    events = [e for e in await asyncio.to_thread(repos.events_for_run, db, run.id, None, t) if e.kind in NOTABLE]
    notes = await asyncio.to_thread(repos.notes_for_run, db, run.id, None, t)
    verdict = await asyncio.to_thread(repos.latest_verdict, db, run.id)
    allowed = await asyncio.to_thread(allowed_now, db, run, refs, t=t, recipe=recipe)
    labels = {v.id: v.label for v in await asyncio.to_thread(repos.vessels_for_run, db, run.id)}
    history = await asyncio.to_thread(repos.chat_for_run, db, run.id, HISTORY)
    images = await asyncio.to_thread(_picture, settings, frames, t)

    rejected: list[str] = []
    call_id: str | None = None
    for _attempt in (1, 2):
        task = chat_task(
            recipe,
            plan,
            refs,
            events,
            notes,
            history,
            question,
            t_display=when,
            allowed=[str(v) for v in VerdictLevel if v in allowed],
            verdict=verdict if verdict is not None and verdict.t <= t + 1e-6 else None,
            rejected=rejected,
            experiment_id=run.experiment_id,
            labels=labels,
        )
        try:
            result = await reasoner(
                task, tier="routine", schema=load_schema("chat_answer"), schema_name="ArgusChatAnswer", images=images
            )
            data, logged = result.data, [*result.failed_calls, result.call]
            reasons = _problems(data, refs)
        except ReasonError as error:
            data, logged, reasons = {}, [error.call], [str(error)]
        for draft in logged:
            call_id = (await asyncio.to_thread(repos.add_model_call, db, run.id, t, draft)).id
        if not reasons:
            used = [r for i in data["refs_used"] if (r := refs.get(i)) is not None]
            chips = [
                {"ref": r.id, "label": r.label, "display": r.display, "t": r.t, "vessel_id": r.vessel_id} for r in used
            ]
            answer = render(unlabelled(data["answer"], "answer"), refs)
            draft = ChatMessageDraft(
                t=t,
                question=question,
                answer=answer,
                body={"answer": data["answer"], "refs_used": data["refs_used"], "chips": chips},
                check_status="passed",
                model_call_id=call_id,
            )
            return await asyncio.to_thread(repos.add_chat_message, db, run.id, draft)
        log.info("chat answer at t=%s rejected: %s", t, reasons)
        rejected = reasons
    answer = fallback_answer(refs, when)
    draft = ChatMessageDraft(
        t=t,
        question=question,
        answer=answer,
        body={"answer": answer, "refs_used": [], "chips": [], "reasons": rejected},
        check_status="fallback",
        model_call_id=call_id,
    )
    return await asyncio.to_thread(repos.add_chat_message, db, run.id, draft)
