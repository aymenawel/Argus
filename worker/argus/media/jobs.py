"""Making videos in the background for the Videos card (spec §10): one job per run and kind at a time, each on its
own thread. A finished video's state is read from its file, so it survives a restart of the worker."""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from argus.config import Settings
from argus.media import MediaError, MediaRefused
from argus.media.make import make_reel, make_timelapse
from argus.media.records import refusal
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database
from argus.storage.files import RunFiles

KINDS = ("timelapse", "reel")
Maker = Callable[..., Path]


class MediaBusy(Exception):
    """That kind of video is already being made for this run."""


class MediaJobs:
    def __init__(
        self,
        db: Database,
        settings: Settings,
        recipes: Mapping[str, Recipe],
        makers: Mapping[str, Maker] | None = None,
    ) -> None:
        self.db, self.settings, self.recipes = db, settings, recipes
        self.makers = dict(makers) if makers is not None else {"timelapse": make_timelapse, "reel": make_reel}
        self._lock = threading.Lock()
        self._jobs: dict[tuple[str, str], dict] = {}  # (run id, kind) → a running or failed job's state

    def start(self, run_id: str, kind: str) -> dict:
        """Start making `kind` for the run; raises MediaRefused (why not) or MediaBusy."""
        reason = refusal(self.db, run_id)
        if reason is not None:
            raise MediaRefused(reason)
        with self._lock:
            if self._jobs.get((run_id, kind), {}).get("state") == "running":
                raise MediaBusy(f"a {kind} is already being made")
            state = {"state": "running", "progress": 0.0}
            self._jobs[(run_id, kind)] = state
        threading.Thread(target=self._run, args=(run_id, kind), daemon=True, name=f"media-{kind}-{run_id}").start()
        return dict(state)

    def _run(self, run_id: str, kind: str) -> None:
        def progress(done: float) -> None:
            with self._lock:
                self._jobs[(run_id, kind)] = {"state": "running", "progress": round(done, 3)}

        try:
            self.makers[kind](self.db, self.settings, self.recipes, run_id, progress=progress)
        except (MediaError, MediaRefused) as error:
            failed = {"state": "failed", "reason": str(error)}
        except Exception as error:  # noqa: BLE001 - the card shows the reason; the worker keeps serving
            failed = {"state": "failed", "reason": f"{type(error).__name__}: {error}"}
        else:
            with self._lock:
                self._jobs.pop((run_id, kind), None)  # ready: the file says so
            return
        with self._lock:
            self._jobs[(run_id, kind)] = failed

    def path(self, run_id: str, kind: str) -> Path | None:
        run = repos.get_run(self.db, run_id)
        return RunFiles(self.settings.data_dir, run.experiment_id, run.id).media_path(kind) if run else None

    def states(self, run_id: str) -> dict[str, dict]:
        found = {}
        for kind in KINDS:
            with self._lock:
                job = self._jobs.get((run_id, kind))
            path = self.path(run_id, kind)
            if job is not None:
                found[kind] = dict(job)
            elif path is not None and path.is_file():
                stat = path.stat()
                made_at = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(timespec="seconds")
                found[kind] = {"state": "ready", "size_bytes": stat.st_size, "made_at": made_at}
            else:
                found[kind] = {"state": "none"}
        return found
