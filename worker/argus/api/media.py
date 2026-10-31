"""Video routes (spec §10): make a run's timelapse or reel in the background, read their states, download them."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from argus.media import MediaRefused
from argus.media.jobs import MediaBusy, MediaJobs
from argus.storage import repos
from argus.storage.db import Database

Kind = Literal["timelapse", "reel"]


def register_media_routes(app: FastAPI, *, db: Database, media: MediaJobs) -> None:
    def run_or_404(run_id: str) -> None:
        if repos.get_run(db, run_id) is None:
            raise HTTPException(status_code=404, detail="run not found")

    @app.post("/api/runs/{run_id}/media/{kind}", status_code=202)
    async def make_media(run_id: str, kind: Kind) -> dict:
        await asyncio.to_thread(run_or_404, run_id)
        try:
            return await asyncio.to_thread(media.start, run_id, kind)
        except (MediaBusy, MediaRefused) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/runs/{run_id}/media")
    def media_states(run_id: str) -> dict:
        run_or_404(run_id)
        return media.states(run_id)

    @app.get("/api/runs/{run_id}/media/{kind}.mp4")
    def media_file(run_id: str, kind: Kind) -> FileResponse:
        run_or_404(run_id)
        path = media.path(run_id, kind)
        if path is None or not path.is_file():
            raise HTTPException(status_code=404, detail=f"no {kind} yet")
        return FileResponse(path, media_type="video/mp4", filename=f"argus-{run_id}-{kind}.mp4")
