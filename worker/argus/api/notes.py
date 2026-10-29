"""Note, verdict and review routes (spec §7, §10): the researcher's own notes, the AI notes and how many answers
the claim checker turned back, the verdict on request, and the researcher's reviews."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from argus.api.events import EventBroker
from argus.config import Settings
from argus.domain import EventKind, Note, NoteDraft, Review, ReviewDraft, Run, Verdict
from argus.pipeline.jobs import RunJobs
from argus.pipeline.verdict import VerdictRefused, run_verdict
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database


class NoteIn(BaseModel):
    t: float = Field(ge=0)
    tag: Literal["observation", "intervention", "question"]
    text: str = Field(min_length=1, max_length=4000)


class NotesView(BaseModel):
    notes: list[Note]
    rejected: int  # AI answers the claim checker turned back (each was retried or written by code)


def register_note_routes(
    app: FastAPI, *, db: Database, broker: EventBroker, settings: Settings, jobs: RunJobs, recipes: dict[str, Recipe]
) -> None:
    def run_or_404(run_id: str) -> Run:
        run = repos.get_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    @app.get("/api/runs/{run_id}/notes")
    def get_notes(run_id: str) -> NotesView:
        run_or_404(run_id)
        attempts = repos.note_attempts_for_run(db, run_id)
        return NotesView(notes=repos.notes_for_run(db, run_id), rejected=sum(not a.passed for a in attempts))

    @app.post("/api/runs/{run_id}/notes", status_code=201)
    def post_note(run_id: str, body: NoteIn) -> Note:
        """The researcher's own words, kept as written (no claim check). An intervention is also an event."""
        run_or_404(run_id)
        evidence = []
        if body.tag == "intervention":
            detail = {"message": body.text}
            event = repos.add_event(
                db,
                run_id,
                vessel_id=None,
                t_start=body.t,
                kind=EventKind.INTERVENTION,
                source="researcher",
                detail=detail,
            )
            evidence.append(event.id)
            data = {"run_id": run_id, "t": body.t, "id": event.id, "kind": str(event.kind), "vessel_id": None}
            broker.publish("event", data | {"detail": detail})
        draft = NoteDraft(
            t=body.t,
            author="researcher",
            level=None,
            tag=body.tag,
            body={"text": body.text},
            refs=[],
            evidence=evidence,
            check_status="researcher",
            model_call_id=None,
        )
        note = repos.add_note(db, run_id, draft)
        broker.publish("note", {"run_id": run_id, "t": note.t, "note": note.model_dump(mode="json")})
        return note

    @app.get("/api/runs/{run_id}/verdict")
    def get_verdict(run_id: str) -> Verdict | None:
        run_or_404(run_id)
        return repos.latest_verdict(db, run_id)

    @app.post("/api/runs/{run_id}/verdict")
    async def ask_verdict(run_id: str) -> Verdict:
        run = await asyncio.to_thread(run_or_404, run_id)
        if jobs.reasoner is None:
            raise HTTPException(status_code=503, detail="reasoning is off: MODEL_API_KEY is not set")
        experiment = await asyncio.to_thread(repos.get_experiment, db, run.experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        try:
            return await run_verdict(
                db, broker, settings, run, recipe=recipes[experiment.recipe_id], reasoner=jobs.reasoner
            )
        except VerdictRefused as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/runs/{run_id}/reviews", status_code=201)
    def post_review(run_id: str, body: ReviewDraft) -> Review:
        run_or_404(run_id)
        return repos.add_review(db, run_id, body)
