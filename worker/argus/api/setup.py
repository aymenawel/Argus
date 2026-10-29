"""Setup wizard routes (spec §8, §10): the saved setup, Muse Spark's draft of the plan from the researcher's words,
the measurement preview on one frame, and the plan, its versions and its lock."""

from __future__ import annotations

import asyncio
import base64

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from argus.api.events import EventBroker
from argus.api.runs import FrameRequest, frame_from, unique_labels
from argus.calibration.run import calibrate
from argus.capture.quality import assess
from argus.domain import Experiment, Plan, PlanDraft, Setup, Vessel
from argus.measure.engine import measure_vessel
from argus.measure.uncertainty import format_measurement
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.reason import ReasonError
from argus.reason.prompts import describe_task
from argus.recipes.model import Recipe
from argus.segment import SegmentError
from argus.segment.outline import outline_polygons
from argus.segment.tracking import assign_to_vessels
from argus.storage import repos
from argus.storage.db import Database

LOCK_NEEDS = ("metric", "direction", "min_effect", "checkpoint_s")  # the prediction a verdict is judged against;
# without a smallest effect that matters, no clear effect could never count as evidence of none
PREVIEW_JPEG_QUALITY = 85


class DescribeIn(BaseModel):
    words: str = Field(min_length=1, max_length=4000)


def register_setup_routes(
    app: FastAPI, *, db: Database, broker: EventBroker, jobs: RunJobs, hub: CameraHub, recipes: dict[str, Recipe]
) -> None:
    def experiment_or_404(experiment_id: str) -> tuple[Experiment, Recipe]:
        experiment = repos.get_experiment(db, experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        return experiment, recipes[experiment.recipe_id]

    @app.get("/api/experiments/{experiment_id}/setup")
    def get_setup(experiment_id: str) -> Setup:
        experiment_or_404(experiment_id)
        return repos.get_setup(db, experiment_id)

    @app.put("/api/experiments/{experiment_id}/setup")
    def put_setup(experiment_id: str, body: Setup) -> Setup:
        experiment_or_404(experiment_id)
        try:
            unique_labels([v.label for v in body.vessels])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if repos.first_locked_plan(db, experiment_id) is not None and repos.runs_for_experiment(db, experiment_id):
            raise HTTPException(status_code=409, detail="the setup is fixed: the plan is locked and a run has started")
        return repos.save_setup(db, experiment_id, body)

    @app.post("/api/experiments/{experiment_id}/describe")
    async def describe(experiment_id: str, body: DescribeIn) -> dict:
        """A draft of the plan, the factor and its conditions from the researcher's words; nothing is saved."""
        experiment, recipe = await asyncio.to_thread(experiment_or_404, experiment_id)
        if jobs.reasoner is None:
            raise HTTPException(status_code=503, detail="reasoning is off: MODEL_API_KEY is not set")
        task, schema = describe_task(experiment, recipe, body.words)
        try:
            result = await jobs.reasoner(task, tier="routine", schema=schema, schema_name="ArgusRecipeDraft")
        except ReasonError as error:
            await asyncio.to_thread(repos.add_model_call, db, None, None, error.call)
            raise HTTPException(status_code=502, detail=f"the draft failed: {error}") from error
        for call in (*result.failed_calls, result.call):
            await asyncio.to_thread(repos.add_model_call, db, None, None, call)
        return result.data

    @app.post("/api/experiments/{experiment_id}/frame")
    async def frame(experiment_id: str, body: FrameRequest) -> Response:
        """A plain frame from the source to draw vessels on: no segmentation, no cost."""
        await asyncio.to_thread(experiment_or_404, experiment_id)
        image = await asyncio.to_thread(frame_from, hub, body)
        ok, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])
        if not ok:
            raise HTTPException(status_code=500, detail="could not encode the frame")
        return Response(jpeg.tobytes(), media_type="image/jpeg")

    @app.post("/api/experiments/{experiment_id}/preview")
    async def preview(experiment_id: str, body: FrameRequest) -> dict:
        """One frame as a run would see it: the calibration, the quality gate and, for the saved setup's vessels,
        their outlines and readings. One SAM image call per concept, none before any vessel is drawn."""
        _, recipe = await asyncio.to_thread(experiment_or_404, experiment_id)
        setup = await asyncio.to_thread(repos.get_setup, db, experiment_id)
        image = await asyncio.to_thread(frame_from, hub, body)
        cal = await asyncio.to_thread(calibrate, image, print_check_mm=setup.print_check_mm, ruler=setup.ruler)
        drawn = setup.vessels  # a vessel without a role yet is measured all the same
        # Named by label, so the quality flags read "saturated:A".
        vessels = [
            Vessel(**(v.model_dump() | {"role": v.role or "treatment"}), id=v.label, run_id="preview") for v in drawn
        ]
        report = await asyncio.to_thread(assess, image, vessels, previous_good=None)
        shape = image.shape[:2]
        masks: dict[str, dict[str, np.ndarray]] = {v.id: {} for v in vessels}
        outlines: dict[str, list] = {v.id: [] for v in vessels}
        for concept in recipe.concepts if vessels else ():
            try:
                result = await jobs.segmenter.image(image, concept.name)
            except SegmentError as error:
                logged = error.call.model_copy(update={"function": "preview"})
                await asyncio.to_thread(repos.add_model_call, db, None, None, logged)
                raise HTTPException(status_code=502, detail=f"segmentation failed: {error}") from error
            logged = result.call.model_copy(update={"function": "preview"})
            await asyncio.to_thread(repos.add_model_call, db, None, None, logged)
            patches = [track.frames[0].patch for track in result.tracks]
            assignment = assign_to_vessels(patches, vessels, shape)
            for vessel in vessels:
                own = [patches[i] for i in assignment[vessel.id]]
                canvas = np.zeros(shape, bool)
                for patch in own:
                    canvas |= patch.to_canvas(*shape)
                    outlines[vessel.id] += outline_polygons(patch)
                masks[vessel.id][concept.name] = canvas  # SAM answered: an empty mask reads as zero
        measured = []
        for vessel in vessels:
            readings = []
            if cal is not None:
                common = dict(t=0.0, frame_id=None, current_reference=cal.reference)
                args = (measure_vessel, recipe, vessel, masks[vessel.id], image, cal)
                result = await asyncio.to_thread(*args, baselines={}, **common)
                if result.lab:  # a colour change is measured from a first reading: on its own frame it starts at 0
                    result = await asyncio.to_thread(*args, baselines=result.lab, **common)
                readings = [
                    {
                        "metric": d.metric,
                        "value": d.value,
                        "unit": d.unit,
                        "display": format_measurement(d.value, d.uncertainty, d.unit),
                    }
                    for d in result.drafts
                ]
            measured.append({"label": vessel.label, "outlines": outlines[vessel.id], "readings": readings})
        ok, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])
        if not ok:
            raise HTTPException(status_code=500, detail="could not encode the frame")
        calibration = None
        if cal is not None:
            draft = cal.to_draft(0.0, {})
            calibration = {
                "card": draft.card,
                "px_per_mm": 1.0 / draft.mm_per_px,
                "rel_uncertainty": draft.rel_uncertainty,
            }
        return {
            "frame_jpeg_b64": base64.b64encode(jpeg.tobytes()).decode("ascii"),
            "calibration": calibration,
            "quality": {"blur": round(report.blur, 1), "flags": list(report.flags)},
            "vessels": measured,
        }

    @app.get("/api/experiments/{experiment_id}/plan")
    def get_plans(experiment_id: str) -> list[Plan]:
        experiment_or_404(experiment_id)
        return repos.get_plans(db, experiment_id)

    @app.put("/api/experiments/{experiment_id}/plan")
    def put_plan(experiment_id: str, body: PlanDraft) -> Plan:
        """Saves the draft; once a version is locked, an edit starts the next version (the first stays judged)."""
        _, recipe = experiment_or_404(experiment_id)
        metrics = recipe.stored_metrics()
        if body.metric is not None and body.metric not in metrics:
            detail = f"the {recipe.title} recipe doesn't measure '{body.metric}': use one of {', '.join(metrics)}"
            raise HTTPException(status_code=422, detail=detail)
        return repos.save_plan_draft(db, experiment_id, body)

    @app.post("/api/experiments/{experiment_id}/plan/lock")
    def lock_plan(experiment_id: str) -> Plan:
        experiment_or_404(experiment_id)
        plans = repos.get_plans(db, experiment_id)
        if not plans:
            raise HTTPException(status_code=422, detail="there is no plan to lock yet")
        latest = plans[-1]
        missing = [name for name in LOCK_NEEDS if getattr(latest, name) is None]
        if latest.locked_at is None and missing:
            raise HTTPException(status_code=422, detail="the plan locks only with " + ", ".join(missing))
        plan = repos.lock_plan(db, experiment_id)
        experiment = repos.get_experiment(db, experiment_id)
        if experiment is not None:
            broker.publish("experiment", experiment.model_dump(mode="json"))
        return plan
