"""Results routes (phase 4): each vessel's readings of a metric and its fitted curve, from that run only."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from argus.analyze.fits import vessel_fits
from argus.recipes.model import Recipe
from argus.recipes.resolve import recipe_for
from argus.storage import repos
from argus.storage.db import Database


def register_results_routes(app: FastAPI, *, db: Database, recipes: dict[str, Recipe]) -> None:
    @app.get("/api/runs/{run_id}/fits")
    def get_fits(run_id: str, metric: str | None = None) -> dict:
        """The plan's metric unless another is asked for (else the recipe's main measurement)."""
        run = repos.get_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        experiment = repos.get_experiment(db, run.experiment_id)
        recipe = recipe_for(db, recipes, experiment)
        plan = repos.first_locked_plan(db, run.experiment_id)
        metric = metric or (plan.metric if plan is not None and plan.metric else recipe.main_measurement)
        metrics = recipe.stored_metrics()
        if metric not in metrics:
            detail = f"the {recipe.title} recipe doesn't measure '{metric}': use one of {', '.join(metrics)}"
            raise HTTPException(status_code=422, detail=detail)
        rows = repos.measurements_for_run(db, run_id, metric=metric)
        fits = vessel_fits(db, run_id, recipe, metric)
        units = {m.id: m.unit for m in recipe.measurements}
        vessels = []
        for vessel in repos.vessels_for_run(db, run_id):
            readings = [[r.t, r.value] for r in rows if r.vessel_id == vessel.id]
            fit = fits.get(vessel.id)
            vessels.append(
                {
                    "vessel_id": vessel.id,
                    "label": vessel.label,
                    "role": str(vessel.role),
                    "condition": vessel.condition.model_dump() if vessel.condition else None,
                    "readings": readings,
                    "fit": asdict(fit) if fit is not None else None,
                }
            )
        return {
            "metric": metric,
            "unit": rows[0].unit if rows else units.get(metric, units.get(metric.rsplit("_", 1)[0], "")),
            "curve": recipe.curve,
            "quantity": (plan.quantity if plan is not None else None) or "level",
            "vessels": vessels,
        }
