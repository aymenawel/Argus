"""Ask Argus routes (D-97): the run's questions and answers, and a new question about the moment at t."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from argus.api.events import EventBroker
from argus.config import Settings
from argus.domain import ChatMessage, Run
from argus.pipeline.chat import ChatRefused, ask_chat
from argus.pipeline.jobs import RunJobs
from argus.recipes.model import Recipe
from argus.recipes.resolve import recipe_for
from argus.storage import repos
from argus.storage.db import Database

MAX_QUESTION = 500


class ChatIn(BaseModel):
    t: float = Field(ge=0)
    question: str

    @field_validator("question")
    @classmethod
    def a_real_question(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= MAX_QUESTION:
            raise ValueError(f"a question is 1 to {MAX_QUESTION} characters")
        return value


def register_chat_routes(
    app: FastAPI, *, db: Database, broker: EventBroker, settings: Settings, jobs: RunJobs, recipes: dict[str, Recipe]
) -> None:
    def run_or_404(run_id: str) -> Run:
        run = repos.get_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    @app.get("/api/runs/{run_id}/chat")
    def get_chat(run_id: str) -> list[ChatMessage]:
        run_or_404(run_id)
        return repos.chat_for_run(db, run_id)

    @app.post("/api/runs/{run_id}/chat", status_code=201)
    async def post_chat(run_id: str, body: ChatIn) -> ChatMessage:
        run = await asyncio.to_thread(run_or_404, run_id)
        if jobs.reasoner is None:
            raise HTTPException(status_code=503, detail="reasoning is off: MODEL_API_KEY is not set")
        experiment = await asyncio.to_thread(repos.get_experiment, db, run.experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        recipe = recipe_for(db, recipes, experiment)
        try:
            message = await ask_chat(db, settings, run, recipe, jobs.reasoner, body.t, body.question)
        except ChatRefused as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        broker.publish("chat", {"run_id": run_id, "message": message.model_dump(mode="json")})
        return message
