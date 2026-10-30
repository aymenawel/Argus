"""Runs as asyncio jobs: start an import or a live run, stop it, and tidy up when the worker shuts down.

A job that crashes is not left hanging as "running": its run is stopped with an `interrupted` event that says
why, and the experiment's state follows the run. A run that ends under a locked plan gets its final verdict.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Coroutine, Mapping, Sequence
from typing import Any

from argus.api.events import EventBroker
from argus.calibration.run import RulerInput
from argus.capture.webcam import CameraSettings
from argus.config import Settings
from argus.domain import EventKind, ExperimentStatus, Run, RunStatus, Vessel
from argus.pipeline.analyzer import RunContext, SamSegmenter, Segmenter
from argus.pipeline.imported import ImportRequest, run_import
from argus.pipeline.live import CameraHub, run_live
from argus.pipeline.verdict import VerdictRefused, run_verdict
from argus.reason import Reasoner
from argus.recipes.model import Recipe
from argus.recipes.resolve import recipe_for
from argus.storage.db import Database
from argus.storage.files import RunFiles
from argus.storage.repos import (
    first_locked_plan,
    get_experiment,
    get_run,
    set_experiment_status,
    set_run_status,
    settle_experiment,
)
from argus.watcher import Watcher, WatcherSettings

STOP_WAIT_S = 30.0


class RunJobs:
    def __init__(
        self,
        db: Database,
        broker: EventBroker,
        settings: Settings,
        recipes: Mapping[str, Recipe],
        hub: CameraHub,
        *,
        segmenter: Segmenter | None = None,
        reasoner: Reasoner | None = None,
    ) -> None:
        self.db, self.broker, self.settings, self.recipes, self.hub = db, broker, settings, recipes, hub
        self.segmenter = segmenter or SamSegmenter(settings)
        self.reasoner = reasoner  # None: no notes or verdicts (no API key)
        self._jobs: dict[str, tuple[asyncio.Task, asyncio.Event]] = {}
        self._verdicts: set[asyncio.Task] = set()

    def running(self, run_id: str) -> bool:
        job = self._jobs.get(run_id)
        return job is not None and not job[0].done()

    def _context(self, run: Run, vessels: Sequence[Vessel]) -> RunContext:
        experiment = get_experiment(self.db, run.experiment_id)
        if experiment is None:
            raise ValueError(f"no experiment {run.experiment_id}")
        return RunContext(
            db=self.db,
            broker=self.broker,
            settings=self.settings,
            files=RunFiles(self.settings.data_dir, run.experiment_id, run.id),
            recipe=recipe_for(self.db, self.recipes, experiment),
            run=run,
            vessels=list(vessels),
            segmenter=self.segmenter,
            reasoner=self.reasoner,
        )

    def start_import(self, run: Run, vessels: Sequence[Vessel], request: ImportRequest) -> None:
        ctx = self._context(run, vessels)
        cancel = asyncio.Event()
        self._spawn(ctx, run_import(ctx, request, cancel=cancel), cancel)

    def start_live(
        self,
        run: Run,
        vessels: Sequence[Vessel],
        camera_index: int,
        camera_settings: CameraSettings | None = None,
        *,
        print_check_mm: float | None = None,
        ruler: RulerInput | None = None,
    ) -> None:
        ctx = self._context(run, vessels)
        source, properties = self.hub.acquire(camera_index, camera_settings)
        watcher = Watcher(ctx.vessels, ctx.recipe.watcher, WatcherSettings.from_recipe(ctx.recipe))
        cancel = asyncio.Event()

        async def live() -> RunStatus:
            try:
                return await run_live(
                    ctx,
                    source,
                    watcher,
                    cancel=cancel,
                    print_check_mm=print_check_mm,
                    ruler=ruler,
                    camera_properties=properties,
                )
            finally:
                source.close()

        self._spawn(ctx, live(), cancel)

    def _spawn(self, ctx: RunContext, job: Coroutine[Any, Any, RunStatus], cancel: asyncio.Event) -> None:
        set_experiment_status(self.db, ctx.run.experiment_id, ExperimentStatus.RUNNING)
        self._jobs[ctx.run.id] = (asyncio.create_task(self._guard(ctx, job)), cancel)

    async def _guard(self, ctx: RunContext, job: Coroutine[Any, Any, RunStatus]) -> RunStatus:
        status = RunStatus.STOPPED
        try:
            status = await job
            if self.reasoner is not None:  # the verdict comes after the run: Stop doesn't wait for it
                verdict = asyncio.create_task(self._final_verdict(ctx))
                self._verdicts.add(verdict)
                verdict.add_done_callback(self._verdicts.discard)
        except asyncio.CancelledError:  # Stop's wait ran out: the page still learns the run stopped
            await asyncio.to_thread(set_run_status, self.db, ctx.run.id, RunStatus.STOPPED)
            ctx.publish("run_status", {"status": str(RunStatus.STOPPED)})
            raise
        except Exception as error:  # a crashed job must not leave its run "running"
            detail = {"reason": "the run stopped on an error", "error": f"{type(error).__name__}: {error}"}
            await ctx.event(0.0, EventKind.INTERRUPTED, "pipeline", detail)
            await asyncio.to_thread(set_run_status, self.db, ctx.run.id, RunStatus.STOPPED)
            ctx.publish("run_status", {"status": str(RunStatus.STOPPED)})
        finally:
            await asyncio.to_thread(settle_experiment, self.db, ctx.run.experiment_id, status)
            self._jobs.pop(ctx.run.id, None)
        return status

    async def _final_verdict(self, ctx: RunContext) -> None:
        """The verdict on the run as it ended (spec §7.3); a refusal (no locked plan, the spend cap) waits for the
        researcher to ask, when the answer says why."""
        run = await asyncio.to_thread(get_run, self.db, ctx.run.id)
        if self.reasoner is None or run is None:
            return
        if await asyncio.to_thread(first_locked_plan, self.db, run.experiment_id) is None:
            return
        with contextlib.suppress(VerdictRefused):
            await run_verdict(self.db, self.broker, self.settings, run, recipe=ctx.recipe, reasoner=self.reasoner)

    async def stop(self, run_id: str) -> bool:
        job = self._jobs.get(run_id)
        if job is None or job[0].done():
            return False
        task, cancel = job
        cancel.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), STOP_WAIT_S)
        except TimeoutError:
            task.cancel()
            await asyncio.wait([task], timeout=5.0)  # let the job record its stop before answering
        return True

    async def shutdown(self) -> None:
        jobs = list(self._jobs.values())
        for _, cancel in jobs:
            cancel.set()
        if jobs:
            _, pending = await asyncio.wait([task for task, _ in jobs], timeout=5.0)
            for task in pending:
                task.cancel()
        for verdict in list(self._verdicts):
            verdict.cancel()
        self.hub.close_all()
        for client in (self.segmenter, self.reasoner):
            close = getattr(client, "aclose", None)
            if close is not None:
                await close()
