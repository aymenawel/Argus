"""The app's preferences (D-77): where everyday model calls run. GET shows the choice and what can be chosen; PUT
saves a new choice, which the next model call follows (no restart)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from argus.config import Settings
from argus.preferences import KEY_FOR, PROVIDERS, ROUTINE_PROVIDER, active_provider, available, options
from argus.storage import repos
from argus.storage.db import Database


class ReasoningChoice(BaseModel):
    provider: str


def register_preference_routes(app: FastAPI, *, db: Database, settings: Settings) -> None:
    def view() -> dict:
        return {
            "provider": active_provider(db, settings),
            "options": options(settings),
            "fixed": {"verdicts": settings.deep_model, "segmentation": settings.segment_model},
        }

    @app.get("/api/preferences/reasoning")
    def get_reasoning() -> dict:
        return view()

    @app.put("/api/preferences/reasoning")
    def put_reasoning(body: ReasoningChoice) -> dict:
        if body.provider not in PROVIDERS:
            raise HTTPException(status_code=422, detail=f"unknown provider: {body.provider}")
        if not available(settings, body.provider):
            raise HTTPException(status_code=422, detail=f"{KEY_FOR[body.provider]} is not set in .env")
        repos.set_preference(db, ROUTINE_PROVIDER, body.provider)
        return view()
