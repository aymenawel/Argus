"""The frame analyzer with a fake segmenter (dark blobs are the concept). No network."""

import asyncio

import cv2
import numpy as np
import pytest
from pydantic import SecretStr

from argus.api.events import EventBroker
from argus.calibration.card import STANDARD
from argus.calibration.run import calibrate
from argus.config import Settings
from argus.domain import ModelCallDraft, Role, RunMode, RunSource, SourceKind, VesselDraft
from argus.pipeline.analyzer import RunContext, Skipped, analyze_frame, correction_paused, segment_with_retries
from argus.recipes.model import Recipe
from argus.segment import Clip, MaskPatch, SegmentError, SegmentResult, Track, TrackFrame
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_vessels,
    create_run,
    detections_for_frame,
    events_for_run,
    frames_for_run,
    measurements_for_run,
)
from tests.helpers import scene_with_bar_on_card_plane

RECIPE = Recipe.model_validate(
    {
        "id": "test",
        "version": 1,
        "title": "Test",
        "default_mode": "smart_trigger",
        "analysis_step_s": 60,
        "curve": "linear",
        "concepts": [{"name": "root"}],
        "measurements": [
            {"id": "length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"},
            {"id": "colour", "family": "colour", "method": "lab_mean", "from": "root", "unit": "Lab"},
        ],
        "main_measurement": "length",
    }
)


def call(status="ok", cost=0.0025, error=None):
    return ModelCallDraft(
        function="segment",
        model="sam-3.1",
        tier="segment",
        images=1,
        cost_usd=cost,
        latency_s=0.1,
        status=status,
        error=error,
    )


class FakeSegmenter:
    """Finds dark blobs. A script of "ok", "empty" or "fail" decides each call; "ok" when the script runs out."""

    def __init__(self):
        self.steps: list[str] = []
        self.calls = 0

    def script(self, steps):
        self.steps = list(steps)

    async def image(self, image_bgr, concept):
        self.calls += 1
        step = self.steps.pop(0) if self.steps else "ok"
        if step == "fail":
            raise SegmentError("ReadTimeout: timed out", call("error", cost=0.0, error="ReadTimeout: timed out"))
        if step == "empty":
            return SegmentResult([], call())
        grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        count, labels, stats, _ = cv2.connectedComponentsWithStats((grey < 60).astype(np.uint8))
        tracks = []
        for i in range(1, count):
            x, y, w, h = (
                int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT)
            )
            patch = MaskPatch(x, y, labels[y : y + h, x : x + w] == i)
            tracks.append(Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.95),)))
        return SegmentResult(tracks, call())

    async def video(self, clip, concept):
        raise NotImplementedError


@pytest.fixture
def scene():
    return scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)


@pytest.fixture
def ctx(db, exp, tmp_path, scene):
    image, mask = scene
    ys, xs = np.nonzero(mask)
    a_roi = [
        (xs.min() - 30, ys.min() - 30),
        (xs.max() + 30, ys.min() - 30),
        (xs.max() + 30, ys.max() + 30),
        (xs.min() - 30, ys.max() + 30),
    ]
    b_roi = [(x, y + 300) for x, y in a_roi]
    run = create_run(db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.VIDEO, paths=["x.mp4"]), time_scale=60)
    vessels = add_vessels(
        db,
        run.id,
        [
            VesselDraft(label="A", role=Role.TREATMENT, roi=[(float(x), float(y)) for x, y in a_roi]),
            VesselDraft(label="B", role=Role.CONTROL, roi=[(float(x), float(y)) for x, y in b_roi]),
        ],
    )
    settings = Settings(model_api_key=SecretStr("k"), data_dir=tmp_path / "data")
    context = RunContext(
        db=db,
        broker=EventBroker(),
        settings=settings,
        files=RunFiles(settings.data_dir, exp.id, run.id),
        recipe=RECIPE,
        run=run,
        vessels=vessels,
        segmenter=FakeSegmenter(),
        calibration=calibrate(image),
    )
    context.retry_delays_s = (0.0, 0.0)
    return context


def kinds(ctx):
    return [str(e.kind) for e in events_for_run(ctx.db, ctx.run.id)]


def calls(ctx):
    with ctx.db.read() as c:
        return [
            r["status"]
            for r in c.execute("SELECT status FROM model_calls WHERE run_id=? ORDER BY rowid", (ctx.run.id,))
        ]


@pytest.mark.anyio
async def test_a_frame_becomes_detections_measurements_and_events(ctx, scene):
    image, _ = scene
    ctx.colour_reference = ctx.calibration.reference  # a run whose colour reference has already settled
    out = await analyze_frame(ctx, 0.0, image, segment=True)
    # A: length + 3 colour readings; B: SAM found nothing there, so its length is a measured 0 (no colour)
    assert out.segmented and out.failed_concepts == [] and out.measurements == 5
    [frame] = frames_for_run(ctx.db, ctx.run.id)
    assert frame.analyzed and (ctx.settings.data_dir / frame.path).is_file()
    [detection] = detections_for_frame(ctx.db, frame.id)
    assert detection.vessel_id == ctx.vessels[0].id and detection.track_key == "A:root:1"
    assert detection.outline and (ctx.settings.data_dir / detection.mask_path).is_file()
    a, b = (v.id for v in ctx.vessels)
    lengths = {m.vessel_id: m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length")}
    assert lengths[a].value == pytest.approx(40, rel=0.05) and lengths[a].frame_id == frame.id
    assert lengths[b].value == 0.0
    published = [e.type for e in ctx.broker.since(0)]
    assert published.count("frame_analyzed") == 1 and published.count("measurement") == 5
    shown = next(
        e.data
        for e in ctx.broker.since(0)
        if e.type == "measurement" and e.data["vessel_id"] == a and e.data["metric"] == "length"
    )
    assert shown["display"].endswith(" mm") and "±" in shown["display"] and shown["run_id"] == ctx.run.id


@pytest.mark.anyio
async def test_nothing_found_is_a_zero_but_a_failure_is_a_gap(ctx, scene):
    image, _ = scene
    ctx.segmenter.script(["empty"])
    await analyze_frame(ctx, 0.0, image, segment=True)
    ctx.segmenter.script(["fail"] * 3)
    out = await analyze_frame(ctx, 60.0, image, segment=True)
    rows = [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == ctx.vessels[0].id]
    assert [r.t for r in rows] == [0.0] and rows[0].value == 0.0
    assert out.failed_concepts == ["root"] and kinds(ctx) == ["segment_failed"]
    assert len(frames_for_run(ctx.db, ctx.run.id)) == 2


@pytest.mark.anyio
async def test_failed_attempts_are_retried_and_each_is_logged(ctx, scene):
    image, _ = scene
    ctx.segmenter.script(["fail", "fail", "ok"])
    out = await analyze_frame(ctx, 0.0, image, segment=True)
    assert out.segmented and calls(ctx) == ["error", "error", "ok"]


@pytest.mark.anyio
async def test_spend_cap_stops_segmenting_but_not_recording(ctx, scene):
    image, _ = scene
    ctx.settings = ctx.settings.model_copy(update={"run_spend_cap_usd": 0.004})
    for t in (0.0, 60.0, 120.0):
        await analyze_frame(ctx, t, image, segment=True)
    assert len(calls(ctx)) == 1 and len(frames_for_run(ctx.db, ctx.run.id)) == 3
    assert kinds(ctx).count("spend") == 1
    assert [e.type for e in ctx.broker.since(0)].count("spend") == 1
    assert measurements_for_run(ctx.db, ctx.run.id, t_from=120.0, metric="colour_l")  # colour on the last masks
    assert not measurements_for_run(ctx.db, ctx.run.id, t_from=60.0, metric="length")  # no new geometry


@pytest.mark.anyio
async def test_without_calibration_nothing_is_measured(ctx, scene):
    image, _ = scene
    ctx.calibration = None
    for t in (0.0, 60.0):
        out = await analyze_frame(ctx, t, image, segment=True)
    assert out.measurements == 0 and ctx.segmenter.calls == 0
    assert kinds(ctx) == ["no_calibration"] and len(frames_for_run(ctx.db, ctx.run.id)) == 2


@pytest.mark.anyio
async def test_colour_drift_beyond_correction_is_flagged(ctx, scene):
    image, _ = scene
    ctx.colour_reference = ctx.calibration.reference  # a run whose colour reference has already settled
    await analyze_frame(ctx, 0.0, image, segment=True)
    tinted = image.copy()
    tinted[..., 0] = (tinted[..., 0] * 0.6).astype(np.uint8)  # less blue everywhere, card neutrals included
    await analyze_frame(ctx, 60.0, tinted, segment=True)
    drift = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "quality"]
    assert len(drift) == 1 and drift[0].detail["colour_drift"] > 6


@pytest.mark.anyio
async def test_injected_masks_count_as_segmented_without_a_call(ctx, scene):
    image, mask = scene
    ys, xs = np.nonzero(mask)
    patch = MaskPatch(int(xs.min()), int(ys.min()), mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1])
    out = await analyze_frame(
        ctx, 0.0, image, segment=False, masks={ctx.vessels[0].id: {"root": [("A:root:1", patch)]}}
    )
    assert out.segmented and ctx.segmenter.calls == 0
    [detection] = detections_for_frame(ctx.db, out.frame_id)
    assert detection.backend == "sam-3.1/video" and detection.track_key == "A:root:1"
    assert measurements_for_run(ctx.db, ctx.run.id, metric="length")[0].value == pytest.approx(40, rel=0.05)


@pytest.mark.anyio
async def test_frames_are_analyzed_concurrently_without_mixing(ctx, scene):
    image, _ = scene
    await asyncio.gather(*(analyze_frame(ctx, t, image, segment=True) for t in (0.0, 60.0, 120.0)))
    a = ctx.vessels[0].id
    times = sorted(m.t for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == a)
    assert times == [0.0, 60.0, 120.0]


@pytest.mark.anyio
async def test_injected_masks_are_per_vessel_a_missing_vessel_is_a_gap(ctx, scene):
    image, _ = scene
    a, b = (v.id for v in ctx.vessels)
    # A's segmentation came back with nothing found; B's never came back (failed): A is a zero, B a gap.
    out = await analyze_frame(ctx, 0.0, image, segment=False, masks={a: {"root": []}})
    lengths = {m.vessel_id: m.value for m in measurements_for_run(ctx.db, ctx.run.id, metric="length")}
    assert out.segmented and lengths == {a: 0.0}


@pytest.mark.anyio
async def test_concurrent_calls_never_spend_past_the_cap(ctx, tmp_path):
    class SlowVideo(FakeSegmenter):
        async def video(self, clip, concept):
            await asyncio.sleep(0.05)  # a SAM video call takes seconds
            return SegmentResult([], call(cost=clip.frame_count * 0.0002))

    ctx.segmenter = SlowVideo()
    ctx.settings = ctx.settings.model_copy(update={"run_spend_cap_usd": 1.0, "sam_concurrency": 6})
    ctx.semaphore = asyncio.Semaphore(6)
    clip = Clip(tmp_path / "c.mp4", frame_count=3000, width=10, height=10)  # $0.60 each
    out = await asyncio.gather(*(segment_with_retries(ctx, clip, "root", t=0.0) for _ in range(6)))
    assert sum(isinstance(r, SegmentResult) for r in out) == 1 and out.count(Skipped("cap")) == 5
    with ctx.db.read() as c:
        spent = c.execute("SELECT SUM(cost_usd) FROM model_calls WHERE run_id=?", (ctx.run.id,)).fetchone()[0]
    assert spent <= 1.0


@pytest.mark.anyio
async def test_uncorrected_colour_is_an_open_event_until_the_card_is_back(ctx, scene):
    image, _ = scene
    ctx.colour_reference = ctx.calibration.reference  # a run whose colour reference has already settled
    x0, y0 = (int(min(c)) for c in zip(*ctx.vessels[0].roi, strict=True))
    x1, y1 = (int(max(c)) for c in zip(*ctx.vessels[0].roi, strict=True))
    hidden = np.full_like(image, 128)  # the card is covered: only vessel A's region is left as it was
    hidden[y0:y1, x0:x1] = image[y0:y1, x0:x1]
    for t, frame in ((0.0, image), (60.0, hidden), (120.0, hidden), (180.0, image)):
        await analyze_frame(ctx, t, frame, segment=True)
    [episode] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "quality"]
    assert (episode.t_start, episode.t_end) == (60.0, 180.0) and "card" in episode.detail["message"]
    a = ctx.vessels[0].id
    rows = [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="colour_l") if m.vessel_id == a]
    assert [(m.t, m.method_version) for m in rows] == [
        (0.0, "lab_mean/1"),
        (60.0, "lab_mean_uncorrected/1"),
        (120.0, "lab_mean_uncorrected/1"),
        (180.0, "lab_mean/1"),
    ]


@pytest.mark.anyio
async def test_concepts_are_segmented_at_the_same_time(ctx, scene):
    image, _ = scene
    ctx.recipe = Recipe.model_validate(
        {**RECIPE.model_dump(by_alias=True), "concepts": [{"name": "root"}, {"name": "seed"}]}
    )
    started, both = set(), asyncio.Event()

    class Meets(FakeSegmenter):
        async def image(self, image_bgr, concept):
            started.add(concept)
            if len(started) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), 2)  # each call waits for the other to have started
            return await super().image(image_bgr, concept)

    ctx.segmenter = Meets()
    assert (await analyze_frame(ctx, 0.0, image, segment=True)).segmented


@pytest.mark.anyio
async def test_a_result_at_sams_object_limit_is_flagged_once(ctx, scene):
    image, _ = scene

    class Full(FakeSegmenter):
        async def image(self, image_bgr, concept):
            patch = MaskPatch(0, 0, np.ones((2, 2), bool))
            return SegmentResult([Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.9),)) for i in range(16)], call())

    ctx.segmenter = Full()
    for t in (0.0, 60.0):
        await analyze_frame(ctx, t, image, segment=True)
    [limit] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "quality"]
    assert (
        limit.detail["concept"] == "root" and limit.detail["objects"] == 16 and "at most 16" in limit.detail["message"]
    )


@pytest.mark.anyio
async def test_a_vessel_with_a_hand_beside_it_gets_a_gap_not_a_reading(ctx, scene):
    image, _ = scene
    a, b = ctx.vessels
    out = await analyze_frame(ctx, 0.0, image, segment=True, quality_flags=(f"occluded:{a.id}",))
    measured = {m.vessel_id for m in measurements_for_run(ctx.db, ctx.run.id)}
    assert measured == {b.id}  # B is still measured
    assert {d.vessel_id for d in detections_for_frame(ctx.db, out.frame_id)} <= {b.id}
    assert a.id not in ctx.last_masks  # the hand's outline is never reused as A's mask


RECIPE_DE = Recipe.model_validate(
    {
        **RECIPE.model_dump(by_alias=True),
        "measurements": [
            *RECIPE.model_dump(by_alias=True)["measurements"],
            {"id": "change", "family": "colour", "method": "delta_e", "from": "root", "unit": "dE00"},
        ],
    }
)


def card_hidden(ctx, image):
    x0, y0 = (int(min(c)) for c in zip(*ctx.vessels[0].roi, strict=True))
    x1, y1 = (int(max(c)) for c in zip(*ctx.vessels[0].roi, strict=True))
    hidden = np.full_like(image, 128)  # the card is covered: only vessel A's region is left as it was
    hidden[y0:y1, x0:x1] = image[y0:y1, x0:x1]
    return hidden


@pytest.mark.anyio
async def test_colour_waits_for_the_camera_to_settle(ctx, scene):
    image, _ = scene
    settling = image.copy()
    settling[..., 0] = (settling[..., 0] * 0.85).astype(np.uint8)  # the camera's white balance still moving
    ctx.recipe, ctx.calibration = RECIPE_DE, calibrate(settling)  # the run calibrated on that first frame
    for i, frame in enumerate([settling] + [image] * 6):
        await analyze_frame(ctx, i * 60.0, frame, segment=True)
    colour = measurements_for_run(ctx.db, ctx.run.id, metric="colour_l")
    assert min(m.t for m in colour) == 120.0  # nothing until the card was read on three frames
    with ctx.db.read() as c:
        rows = c.execute("SELECT t FROM calibrations WHERE run_id=?", (ctx.run.id,)).fetchall()
    assert [r["t"] for r in rows] == [120.0]  # the settled reference is kept as evidence
    change = measurements_for_run(ctx.db, ctx.run.id, metric="change")
    assert change and all(m.value < 1.0 for m in change)  # no offset from the unsettled first frame


def test_correction_pauses_above_6_and_resumes_below_5():
    assert not correction_paused(5.9, paused=False) and correction_paused(6.1, paused=False)
    assert correction_paused(5.5, paused=True) and not correction_paused(4.9, paused=True)
    assert correction_paused(None, paused=False)


@pytest.mark.anyio
async def test_uncorrected_change_is_measured_from_the_start(ctx, scene):
    image, _ = scene
    ctx.recipe = RECIPE_DE
    for i in range(4):  # three to settle, then corrected readings
        await analyze_frame(ctx, i * 60.0, image, segment=True)
    await analyze_frame(ctx, 240.0, card_hidden(ctx, image), segment=True)
    a = ctx.vessels[0].id
    [late] = [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="change") if m.t == 240.0 and m.vessel_id == a]
    assert late.method_version == "delta_e_uncorrected/1" and late.value < 1.0
