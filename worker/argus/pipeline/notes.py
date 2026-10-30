"""AI notes during a run (spec §7.2): on notable events and on a schedule, every number a {ref} token the claim
checker passed, retried once with its reasons, else written by code from the refs. Every answer is kept as a note
attempt and every call is logged. Quiet stretches collapse into one note; the spend cap pauses notes, once, with a
note that says so.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from argus.analyze.ceiling import NOISE_FACTOR
from argus.claims.checker import TOKEN, check_note, render_note
from argus.claims.fallback import fallback_note
from argus.claims.refs import NOTABLE, RefTable, build_refs
from argus.claims.schema import schema_errors
from argus.domain import ModelCallDraft, Note, NoteAttemptDraft, NoteDraft, RunEvent, VerdictLevel
from argus.pipeline.verdict import allowed_now
from argus.reason import ReasonError
from argus.reason.prompts import load_schema, note_task, snapshot_jpeg
from argus.recipes.model import Recipe
from argus.storage.repos import (
    add_model_call,
    add_note,
    add_note_attempt,
    events_for_run,
    extend_note,
    first_locked_plan,
    models_of_calls,
    notes_for_run,
    run_spend_usd,
)

if TYPE_CHECKING:
    from argus.pipeline.analyzer import RunContext

log = logging.getLogger(__name__)
Level = Literal["event", "checkpoint"]
EXPECTED_NOTE_USD = 0.02  # a Muse Spark note with one snapshot (KB 05: under a cent)
TRIGGERS = frozenset({"intervention", "rule", "camera_moved", "segment_failed"})  # never a watcher change alone
CHECKPOINT_STEPS = 24
MIN_INTERVAL_S = 120.0
TWICE_REJECTED = "the model's answers failed the claim check twice"
PAUSED = "notes paused: spend cap"


def note_interval_s(recipe: Recipe) -> float:
    """A checkpoint note every 24 analysis steps, and never more often than every 2 minutes."""
    return max(MIN_INTERVAL_S, CHECKPOINT_STEPS * recipe.analysis_step_s)


def _cited(data: dict) -> list[str]:
    """Every ref the answer cites: the ones it lists and the tokens in its text."""
    return list(dict.fromkeys([*(data.get("refs_used") or []), *TOKEN.findall(json.dumps(data, ensure_ascii=False))]))


class NoteWriter:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.interval = note_interval_s(ctx.recipe)
        self.last_t = 0.0  # the run's start counts as the last note
        self.event_waiting = False  # a notable event came too soon after the last note: it waits for the gap
        self.paused = False  # the spend cap paused notes, and one note said so
        self.last: Note | None = None
        self.last_quiet = False  # the last note was a checkpoint where code saw no change
        self.values: dict[str, float] = {}  # each reading's value when the last note was written
        self.seen: set[str] = set()

    def fresh_events(self, t: float) -> list[RunEvent]:
        """The events up to t this writer hasn't seen yet (blocking: call it in a worker thread). An import's scan
        stores events across the whole video before the first sample is measured, so later ones wait their turn."""
        events = events_for_run(self.ctx.db, self.ctx.run.id, t_from=self.last_t - self.interval, t_to=t)
        new = [e for e in events if e.id not in self.seen]
        self.seen.update(e.id for e in new)
        return new

    def due(self, t: float, new_events: Sequence[RunEvent]) -> Level | None:
        """An event note for an intervention, a rule crossing, a camera move or a failed segmentation, at least a
        quarter of the interval after the last note; a checkpoint note once the interval has passed."""
        if self.ctx.reasoner is None or self.paused:
            return None
        if any(e.kind in TRIGGERS for e in new_events):
            self.event_waiting = True
        since = t - self.last_t
        if self.event_waiting and since >= self.interval / 4:
            return "event"
        return "checkpoint" if since >= self.interval else None

    def _quiet(self, refs: RefTable) -> bool:
        """Code's "no change", never the model's: every reading within 3 × its metric's noise floor of where it
        stood at the last note (before the first note: of its first reading). No readings or no noise floor yet
        is never quiet."""
        readings = [r for r in (refs.get(i) for i in refs.ids() if i.startswith("m:")) if r is not None]
        if not readings:
            return False
        for ref in readings:
            _, label, metric = ref.id.split(":", 2)
            noise = refs.get(f"noise:{metric}")
            if noise is None:
                return False
            before = self.values.get(ref.id)
            change = refs.get(f"chg:{label}:{metric}")
            moved = ref.value - before if before is not None else (change.value if change is not None else 0.0)
            if abs(moved) > NOISE_FACTOR * noise.value:
                return False
        return True

    async def _reserve(self) -> bool:
        """Check the spend cap and reserve a note's expected cost together, as segmentation does."""
        ctx = self.ctx
        async with ctx.spend_lock:
            spent = await asyncio.to_thread(run_spend_usd, ctx.db, ctx.run.id)
            if spent + ctx.reserved_usd + EXPECTED_NOTE_USD > ctx.settings.run_spend_cap_usd:
                return False
            ctx.reserved_usd += EXPECTED_NOTE_USD
            return True

    async def _add(
        self, t: float, level: Level, refs: RefTable, body: dict, cited: list[str], evidence: list[str], **kw: Any
    ) -> Note:
        used = [r for i in cited if (r := refs.get(i)) is not None]
        rows = [e for r in used for e in r.evidence]
        # One evidence chip per cited number: what it reads and where it sits in the run, for the feed.
        chips = [
            {"ref": r.id, "label": r.label, "display": r.display, "t": r.t, "vessel_id": r.vessel_id} for r in used
        ]
        draft = NoteDraft(
            t=t,
            author="ai",
            level=level,
            tag=None,
            body=body | {"chips": chips},
            refs=cited,
            evidence=list(dict.fromkeys([*evidence, *rows])),
            **kw,
        )
        note = await asyncio.to_thread(add_note, self.ctx.db, self.ctx.run.id, draft)
        self.last = note
        self.values = {i: r.value for i in refs.ids() if i.startswith("m:") and (r := refs.get(i)) is not None}
        await self._publish(t, note)
        return note

    async def _publish(self, t: float, note: Note) -> None:
        """The note for the page, with the model that wrote it (Muse Spark or Muse Spark Open; none for code)."""
        call = note.model_call_id
        models = await asyncio.to_thread(models_of_calls, self.ctx.db, [call]) if call else {}
        self.ctx.publish("note", {"t": t, "note": note.model_dump(mode="json"), "model": models.get(call or "")})

    async def write(self, t: float, level: Level, *, image_bgr: np.ndarray) -> Note | None:
        """A note at t, checked, retried once, or written by code. Notes are an add-on to measuring: an unexpected
        error becomes a code-written note that says what failed (or no note), never an end to the run."""
        try:
            return await self._write(t, level, image_bgr=image_bgr)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.exception("note at t=%s failed", t)
            reason = f"the note failed: {type(error).__name__}: {error}"
            try:
                plan = await asyncio.to_thread(first_locked_plan, self.ctx.db, self.ctx.run.experiment_id)
                refs = await asyncio.to_thread(
                    build_refs, self.ctx.db, self.ctx.run.id, t, recipe=self.ctx.recipe, plan=plan
                )
                body = fallback_note(level, refs, reason=reason)
                return await self._add(
                    t, level, refs, body, body["refs_used"], [], check_status="fallback", model_call_id=None
                )
            except Exception:
                log.exception("the code-written note at t=%s failed too", t)
                return None

    async def _write(self, t: float, level: Level, *, image_bgr: np.ndarray) -> Note | None:
        ctx = self.ctx
        self.last_t, self.event_waiting = t, False
        if ctx.reasoner is None or self.paused:
            return None
        plan = await asyncio.to_thread(first_locked_plan, ctx.db, ctx.run.experiment_id)
        refs = await asyncio.to_thread(build_refs, ctx.db, ctx.run.id, t, recipe=ctx.recipe, plan=plan)
        quiet = level == "checkpoint" and self._quiet(refs)
        if quiet and self.last_quiet and self.last is not None:  # nothing moved since a quiet note: it goes on
            self.last = await asyncio.to_thread(extend_note, ctx.db, self.last.id, t)
            await self._publish(t, self.last)
            return self.last
        self.last_quiet = quiet

        events = [e for e in await asyncio.to_thread(events_for_run, ctx.db, ctx.run.id, None, t) if e.kind in NOTABLE]
        notes = await asyncio.to_thread(notes_for_run, ctx.db, ctx.run.id, None, t)
        allowed = await asyncio.to_thread(allowed_now, ctx.db, ctx.run, refs, t=t, recipe=ctx.recipe)
        names = [str(v) for v in VerdictLevel if v in allowed]
        labels = {v.id: v.label for v in ctx.vessels}
        images = (await asyncio.to_thread(snapshot_jpeg, image_bgr, ctx.settings.snapshot_px),)
        rejected: list[str] = []
        call_id: str | None = None
        for attempt in (1, 2):
            if not await self._reserve():
                self.paused = True
                body = fallback_note(level, refs, reason=PAUSED)
                return await self._add(
                    t, level, refs, body, body["refs_used"], [], check_status="fallback", model_call_id=None
                )
            task = note_task(
                level,
                ctx.recipe,
                plan,
                refs,
                events,
                notes,
                rejected=rejected,
                allowed=names,
                experiment_id=ctx.run.experiment_id,
                labels=labels,
            )
            started = time.perf_counter()
            try:
                try:
                    result = await ctx.reasoner(
                        task, tier="routine", schema=load_schema("note"), schema_name="ArgusNote", images=images
                    )
                    data, logged = result.data, [*result.failed_calls, result.call]
                    # The schema first: a wrong shape is a reason to retry, never a crash in the checks after it.
                    reasons = schema_errors(data, load_schema("note")) or check_note(
                        data, refs, allowed=allowed, evidence={e.id for e in events}
                    )
                except ReasonError as error:
                    data, logged, reasons = {}, [error.call], [str(error)]
                except asyncio.CancelledError:  # a forced stop: the request may be billed, so it is logged
                    add_model_call(ctx.db, ctx.run.id, t, self._cancelled(started))
                    raise
                for call in logged:
                    call_id = (await asyncio.to_thread(add_model_call, ctx.db, ctx.run.id, t, call)).id
            finally:
                ctx.reserved_usd -= EXPECTED_NOTE_USD
            kept = await asyncio.to_thread(
                add_note_attempt,
                ctx.db,
                ctx.run.id,
                NoteAttemptDraft(
                    t=t, attempt=attempt, raw=data, reasons=reasons, passed=not reasons, model_call_id=call_id
                ),
            )
            if not reasons:
                body = render_note(data, refs) | {"written_by": "model"}
                evidence = list(data.get("evidence_ids") or [])
                return await self._add(
                    t, level, refs, body, _cited(data), evidence, check_status="passed", model_call_id=call_id
                )
            ctx.publish("note_rejected", {"t": t, "attempt_id": kept.id, "reasons": reasons})
            rejected = reasons
        body = fallback_note(level, refs, reason=TWICE_REJECTED)
        return await self._add(
            t, level, refs, body, body["refs_used"], [], check_status="fallback", model_call_id=call_id
        )

    def _cancelled(self, started: float) -> ModelCallDraft:
        return ModelCallDraft(
            function="note",
            model=self.ctx.settings.routine_model,
            tier="routine",
            cost_usd=EXPECTED_NOTE_USD,
            latency_s=round(time.perf_counter() - started, 3),
            status="error",
            error="cancelled",
        )
