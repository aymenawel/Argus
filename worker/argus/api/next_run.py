"""Next-run routes (D-80): the latest suggestion for a run, and a new one once the run has ended."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException

from argus.config import Settings
from argus.domain import NextRun, Run
from argus.pipeline.jobs import RunJobs
from argus.pipeline.next_run import NextRunRefused, suggest_next_run
from argus.recipes.model import Recipe
from argus.recipes.resolve import recipe_for
from argus.storage import repos
from argus.storage.db import Database


def register_next_run_routes(
    app: FastAPI, *, db: Database, settings: Settings, jobs: RunJobs, recipes: dict[str, Recipe]
) -> None:
    def run_or_404(run_id: str) -> Run:
        run = repos.get_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    @app.get("/api/runs/{run_id}/next-run")
    def get_next_run(run_id: str) -> NextRun | None:
        run_or_404(run_id)
        return repos.latest_next_run(db, run_id)

    @app.post("/api/runs/{run_id}/next-run", status_code=201)
    async def post_next_run(run_id: str) -> NextRun:
        """Code's numbers, with Muse Wonder's reasons when reasoning is on (code writes them otherwise)."""
        run = await asyncio.to_thread(run_or_404, run_id)
        experiment = await asyncio.to_thread(repos.get_experiment, db, run.experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        try:
            return await suggest_next_run(db, run, recipe_for(db, recipes, experiment), jobs.reasoner, settings)
        except NextRunRefused as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
