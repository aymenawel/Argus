"""The FastAPI app. Run with: uvicorn --factory argus.api.app:app_from_env"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from argus.api.events import EventBroker, event_stream
from argus.config import Settings, load_settings
from argus.domain import Experiment
from argus.recipes.loader import load_all
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database

VERSION = "0.1.0"


class ExperimentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    recipe_id: str


class RecipeSummary(BaseModel):
    id: str
    version: int
    title: str
    main_measurement: str


def create_app(
    settings: Settings,
    db: Database,
    broker: EventBroker,
    recipes: dict[str, Recipe],
    *,
    close_db_on_shutdown: bool = False,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if close_db_on_shutdown:
            db.close()

    app = FastAPI(title="Argus worker", version=VERSION, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": VERSION}

    @app.get("/api/recipes")
    def list_recipes() -> list[RecipeSummary]:
        return [RecipeSummary(**r.model_dump(include=set(RecipeSummary.model_fields))) for r in recipes.values()]

    @app.get("/api/experiments")
    def list_experiments() -> list[Experiment]:
        return repos.list_experiments(db)

    @app.post("/api/experiments", status_code=201)
    def create_experiment(body: ExperimentCreate) -> Experiment:
        recipe = recipes.get(body.recipe_id)
        if recipe is None:
            raise HTTPException(status_code=422, detail=f"unknown recipe: {body.recipe_id}")
        experiment = repos.create_experiment(db, body.title, recipe.id, recipe.version)
        broker.publish("experiment", experiment.model_dump(mode="json"))
        return experiment

    @app.get("/api/experiments/{experiment_id}")
    def get_experiment(experiment_id: str) -> Experiment:
        experiment = repos.get_experiment(db, experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        return experiment

    @app.get("/api/events")
    async def events(last_event_id: str | None = Header(default=None)) -> StreamingResponse:
        last = int(last_event_id) if last_event_id and last_event_id.isdigit() else None
        return StreamingResponse(
            event_stream(broker, last),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def app_from_env() -> FastAPI:
    settings = load_settings()
    return create_app(
        settings,
        Database(settings.data_dir / "argus.sqlite"),
        EventBroker(),
        load_all(settings.recipes_dir),
        close_db_on_shutdown=True,
    )
