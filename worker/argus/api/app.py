"""The FastAPI app. Run with: uvicorn --factory argus.api.app:app_from_env"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from argus.api.cameras import register_camera_routes
from argus.api.events import EventBroker, event_stream
from argus.api.notes import register_note_routes
from argus.api.runs import register_run_routes
from argus.api.setup import register_setup_routes
from argus.config import Settings, load_settings
from argus.domain import Experiment
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.reason import SettingsReasoner
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


class MetricInfo(BaseModel):
    id: str  # as readings are stored (a lab_mean measurement stores _l, _a and _b)
    unit: str


class RecipeDetail(RecipeSummary):
    """What the setup wizard offers: concepts to find vessels by, metrics a plan may predict, and rivals."""

    concepts: list[str]
    metrics: list[MetricInfo]
    rivals: list[str]


def create_app(
    settings: Settings,
    db: Database,
    broker: EventBroker,
    recipes: dict[str, Recipe],
    *,
    jobs: RunJobs | None = None,
    hub: CameraHub | None = None,
    close_db_on_shutdown: bool = False,
) -> FastAPI:
    hub = hub or CameraHub()
    if jobs is None:
        reasoner = SettingsReasoner(settings) if settings.model_api_key is not None else None
        jobs = RunJobs(db, broker, settings, recipes, hub, reasoner=reasoner)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Runs still marked running were cut off when the worker last stopped (argus dev restarts it on save).
        await asyncio.to_thread(repos.stop_interrupted_runs, db)
        yield
        await jobs.shutdown()
        if close_db_on_shutdown:
            db.close()

    app = FastAPI(title="Argus worker", version=VERSION, lifespan=lifespan)
    app.state.jobs = jobs
    app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": VERSION}

    @app.get("/api/recipes")
    def list_recipes() -> list[RecipeSummary]:
        return [RecipeSummary(**r.model_dump(include=set(RecipeSummary.model_fields))) for r in recipes.values()]

    @app.get("/api/recipes/{recipe_id}")
    def get_recipe(recipe_id: str) -> RecipeDetail:
        recipe = recipes.get(recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="recipe not found")
        units = {m.id: m.unit for m in recipe.measurements}
        metrics = [
            MetricInfo(id=name, unit=units.get(name, units.get(name.rsplit("_", 1)[0], "")))
            for name in recipe.stored_metrics()
        ]
        return RecipeDetail(
            **recipe.model_dump(include=set(RecipeSummary.model_fields)),
            concepts=[c.name for c in recipe.concepts],
            metrics=metrics,
            rivals=list(recipe.rivals),
        )

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
        return StreamingResponse(
            event_stream(broker, last_event_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    register_run_routes(app, db=db, settings=settings, jobs=jobs, hub=hub)
    register_setup_routes(app, db=db, broker=broker, jobs=jobs, hub=hub, recipes=recipes)
    register_note_routes(app, db=db, broker=broker, settings=settings, jobs=jobs, recipes=recipes)
    register_camera_routes(app, hub=hub)
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
