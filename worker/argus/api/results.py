"""Results routes (phase 4): each vessel's readings of a metric and its fitted curve, from that run only."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from argus.analyze.fits import fits_view
from argus.recipes.model import Recipe
from argus.storage.db import Database


def register_results_routes(app: FastAPI, *, db: Database, recipes: dict[str, Recipe]) -> None:
    @app.get("/api/runs/{run_id}/fits")
    def get_fits(run_id: str, metric: str | None = None) -> dict:
        """The plan's metric unless another is asked for (else the recipe's main measurement)."""
        try:
            return fits_view(db, recipes, run_id, metric)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
