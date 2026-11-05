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
from argus.pipeline.pointing import CROP_MARGIN_PX
from argus.recipes.model import Concept, Recipe
from argus.rois import roi_box, roi_mask
from argus.segment import Clip, MaskPatch, ObjectPrompt, SegmentError, SegmentResult, Track, TrackFrame
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_vessels,
    create_run,
    detections_for_frame,
    events_for_run,
    frames_for_run,
    measurements_for_run,
    sam_answers_for_run,
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
        self.pointed_steps: list[str] = []  # "ok" (the crop's dark blobs), "empty", "whole", "spill" or "fail"
        self.pointed_asks: list[tuple[str, list]] = []  # (concept, prompts) per pointed call

    def script(self, steps):
        self.steps = list(steps)

    async def pointed(self, image_bgr, concept, prompts):
        self.pointed_asks.append((concept, list(prompts)))
        step = self.pointed_steps.pop(0) if self.pointed_steps else "ok"
        if step == "fail":
            raise SegmentError("ReadTimeout: timed out", call("error", cost=0.0, error="ReadTimeout: timed out"))
        if step == "empty":
            return SegmentResult([], call())
        if step == "whole":  # SAM outlined the whole crop: the dish, not what changed in it
            whole = MaskPatch(0, 0, np.ones(image_bgr.shape[:2], bool))
            return SegmentResult([Track("obj1", concept, (TrackFrame(0, whole, 0.9),))], call())
        if step == "bloat-second":  # the first object traced well, the second far past the change it was shown
            grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            x1, y1, x2, y2 = prompts[0].box
            good = MaskPatch(x1, y1, grey[y1 : y2 + 1, x1 : x2 + 1] < 60)
            bloated = MaskPatch(0, 0, np.ones((grey.shape[0], grey.shape[1] // 2), bool))
            tracks = [
                Track("obj1", concept, (TrackFrame(0, good, 0.9),)),
                Track("obj2", concept, (TrackFrame(0, bloated, 0.9),)),
            ]
            return SegmentResult(tracks, call())
        if step == "spill":  # SAM traced far past the box it was given: most of the crop, under the vessel guard
            h, w = image_bgr.shape[:2]
            spill = MaskPatch(0, 0, np.ones((h, int(w * 0.5)), bool))
            return SegmentResult([Track("obj1", concept, (TrackFrame(0, spill, 0.9),))], call())
        return SegmentResult(dark_tracks(image_bgr, concept), call())

    async def image(self, image_bgr, concept):
        self.calls += 1
        step = self.steps.pop(0) if self.steps else "ok"
        if step == "fail":
            raise SegmentError("ReadTimeout: timed out", call("error", cost=0.0, error="ReadTimeout: timed out"))
        if step == "empty":
            return SegmentResult([], call())
        return SegmentResult(dark_tracks(image_bgr, concept), call())

    async def video(self, clip, concept):
        raise NotImplementedError


def dark_tracks(image_bgr, concept):
    """Every dark blob, as SAM's tracks."""
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    count, labels, stats, _ = cv2.connectedComponentsWithStats((grey < 60).astype(np.uint8))
    tracks = []
    for i in range(1, count):
        x, y, w, h = (
            int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT)
        )
        patch = MaskPatch(x, y, labels[y : y + h, x : x + w] == i)
        tracks.append(Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.95),)))
    return tracks


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
async def test_a_video_result_at_sams_object_limit_is_flagged_once(ctx, tmp_path):
    def sixteen(concept):
        patch = MaskPatch(0, 0, np.ones((2, 2), bool))
        return SegmentResult([Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.9),)) for i in range(16)], call())

    class Full(FakeSegmenter):
        async def video(self, clip, concept):
            return sixteen(concept)

    ctx.segmenter = Full()
    clip = Clip(tmp_path / "c.mp4", frame_count=60, width=10, height=10)
    for t in (0.0, 60.0):
        await segment_with_retries(ctx, clip, "root", t=t)
    [limit] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "quality"]
    assert (
        limit.detail["concept"] == "root" and limit.detail["objects"] == 16 and "at most 16" in limit.detail["message"]
    )


@pytest.mark.anyio
async def test_an_image_result_past_sixteen_objects_is_not_a_limit(ctx, scene):
    """SAM's 16-object cap is for video and pointed requests: by name on one image it found 24 of 24 coins (KB 04)
    and 133 yeast cells, so many objects on an image are no sign that some were left out (D-103)."""
    image, _ = scene

    class Many(FakeSegmenter):
        async def image(self, image_bgr, concept):
            patch = MaskPatch(0, 0, np.ones((2, 2), bool))
            return SegmentResult([Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.9),)) for i in range(40)], call())

    ctx.segmenter = Many()
    await segment_with_retries(ctx, image, "root", t=0.0)
    assert "quality" not in kinds(ctx)


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


def bar(mask):
    """The scene's bar as SAM's mask patch, for injected (video-mode) masks."""
    ys, xs = np.nonzero(mask)
    return MaskPatch(int(xs.min()), int(ys.min()), mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1])


def misses(ctx):
    return [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "missed"]


@pytest.mark.anyio
async def test_after_a_first_sighting_nothing_found_is_a_miss_not_a_zero(ctx, scene):
    """Once SAM has found the root in A, a frame where it finds nothing is a gap with a missed event, not a zero;
    B, never seen, reads zero throughout (D-90)."""
    image, mask = scene
    a, b = (v.id for v in ctx.vessels)
    found = {a: {"root": [("A:root:1", bar(mask))]}, b: {"root": []}}
    lost = {a: {"root": []}, b: {"root": []}}
    for t, masks in ((0.0, found), (60.0, lost), (120.0, lost), (180.0, found)):
        await analyze_frame(ctx, t, image, segment=False, masks=masks)
    lengths = measurements_for_run(ctx.db, ctx.run.id, metric="length")
    assert [m.t for m in lengths if m.vessel_id == a] == [0.0, 180.0]
    assert [m.value for m in lengths if m.vessel_id == b] == [0.0] * 4
    [miss] = misses(ctx)
    assert (miss.vessel_id, miss.t_start, miss.t_end, miss.source) == (a, 60.0, 180.0, "pipeline")
    assert miss.detail["concept"] == "root" and miss.detail["last_seen_t"] == 0.0
    assert miss.detail["message"].startswith("SAM found no root in A after finding it at ")
    answers = sam_answers_for_run(ctx.db, ctx.run.id)
    assert [x.found for x in answers if x.vessel_id == a] == [1, 0, 0, 1]
    assert [x.found for x in answers if x.vessel_id == b] == [0, 0, 0, 0]
    published = [e.data for e in ctx.broker.since(0) if e.type == "event" and e.data["kind"] == "missed"]
    assert [e.get("t_end") for e in published] == [None, 180.0]


@pytest.mark.anyio
async def test_a_miss_still_open_at_the_end_stays_open(ctx, scene):
    image, mask = scene
    a = ctx.vessels[0].id
    for t, patches in ((0.0, [("A:root:1", bar(mask))]), (60.0, [])):
        await analyze_frame(ctx, t, image, segment=False, masks={a: {"root": patches}})
    [miss] = misses(ctx)
    assert miss.t_start == 60.0 and miss.t_end is None  # never found again


@pytest.mark.anyio
async def test_a_concept_that_can_vanish_reads_zero_after_a_sighting(ctx, scene):
    """Foam can really collapse: its empty answers stay zeros, with no missed event."""
    image, mask = scene
    a = ctx.vessels[0].id
    ctx.recipe = RECIPE.model_copy(update={"concepts": [Concept(name="root", can_vanish=True)]})
    for t, patches in ((0.0, [("A:root:1", bar(mask))]), (60.0, [])):
        await analyze_frame(ctx, t, image, segment=False, masks={a: {"root": patches}})
    lengths = [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == a]
    assert [m.t for m in lengths] == [0.0, 60.0] and lengths[1].value == 0.0
    assert misses(ctx) == []


@pytest.mark.anyio
async def test_a_hand_in_front_neither_ends_nor_repeats_a_miss(ctx, scene):
    image, mask = scene
    a = ctx.vessels[0].id
    seen = {a: {"root": [("A:root:1", bar(mask))]}}
    await analyze_frame(ctx, 0.0, image, segment=False, masks=seen)
    await analyze_frame(ctx, 60.0, image, segment=False, masks={a: {"root": []}})
    await analyze_frame(ctx, 120.0, image, segment=False, masks=seen, quality_flags=(f"occluded:{a}",))
    await analyze_frame(ctx, 180.0, image, segment=False, masks=seen)
    [miss] = misses(ctx)
    assert (miss.t_start, miss.t_end) == (60.0, 180.0)  # what SAM found behind the hand doesn't end the miss
    assert [x.t for x in sam_answers_for_run(ctx.db, ctx.run.id) if x.vessel_id == a] == [0.0, 60.0, 180.0]


@pytest.mark.anyio
async def test_two_frames_at_once_open_one_miss(ctx, scene):
    image, mask = scene
    a = ctx.vessels[0].id
    await analyze_frame(ctx, 0.0, image, segment=False, masks={a: {"root": [("A:root:1", bar(mask))]}})
    await asyncio.gather(*(analyze_frame(ctx, t, image, segment=False, masks={a: {"root": []}}) for t in (60.0, 120.0)))
    assert len(misses(ctx)) == 1


@pytest.mark.anyio
async def test_losing_one_concept_keeps_the_other(ctx, scene):
    image, mask = scene
    a = ctx.vessels[0].id
    ctx.recipe = RECIPE.model_copy(
        update={
            "concepts": [Concept(name="root"), Concept(name="bean")],
            "measurements": [
                RECIPE.measurements[0],
                RECIPE.measurements[0].model_copy(update={"id": "bean_length", "source": "bean"}),
            ],
        }
    )
    both = {a: {"root": [("A:root:1", bar(mask))], "bean": [("A:bean:1", bar(mask))]}}
    await analyze_frame(ctx, 0.0, image, segment=False, masks=both)
    await analyze_frame(ctx, 60.0, image, segment=False, masks={a: {"root": [], "bean": both[a]["bean"]}})
    rows = [m for m in measurements_for_run(ctx.db, ctx.run.id) if m.vessel_id == a]
    assert [m.t for m in rows if m.metric == "bean_length"] == [0.0, 60.0]
    assert [m.t for m in rows if m.metric == "length"] == [0.0]
    [miss] = misses(ctx)
    assert miss.detail["concept"] == "root"


@pytest.mark.anyio
async def test_prompts_go_to_the_pointed_segmenter_and_are_logged(ctx, scene):
    """A request with box prompts is SAM pointed at them (D-92): one logged call, priced like an image."""
    image, _ = scene
    asked = []

    class Pointed(FakeSegmenter):
        async def pointed(self, image_bgr, concept, prompts):
            asked.append((concept, list(prompts)))
            return SegmentResult([], call())

    ctx.segmenter = Pointed()
    prompts = [ObjectPrompt((0, 0, 9, 9))]
    result = await segment_with_retries(ctx, image, "root", t=0.0, prompts=prompts)
    assert isinstance(result, SegmentResult)
    assert asked == [("root", prompts)] and ctx.segmenter.calls == 0  # never asked by name
    assert calls(ctx) == ["ok"]


def appearing(ctx, *others):
    """The test recipe with its root marked as appearing (D-92), plus concepts that don't."""
    ctx.recipe = RECIPE.model_copy(
        update={"concepts": [Concept(name="root", appears=True), *(Concept(name=c) for c in others)]}
    )


def plain(image, mask):
    """The scene before the root grew: the bar painted over with the card around it."""
    return cv2.inpaint(image, mask.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)


async def start(ctx, image, mask):
    """Three kept frames of the start: the reference each vessel's change is measured from."""
    for t in (0.0, 60.0, 120.0):
        await analyze_frame(ctx, t, plain(image, mask), segment=True)
    assert ctx.segmenter.pointed_asks == []  # never pointed while the reference is being taken


def drawn_by(ctx, frame_id):
    a = ctx.vessels[0].id
    return [d.backend for d in detections_for_frame(ctx.db, frame_id) if d.vessel_id == a]


def via_of_a(ctx, t):
    a = ctx.vessels[0].id
    return next(x.via for x in sam_answers_for_run(ctx.db, ctx.run.id) if x.vessel_id == a and x.t == t)


def last_length_of_a(ctx):
    a = ctx.vessels[0].id
    return [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == a][-1]


@pytest.mark.anyio
async def test_an_empty_answer_where_the_vessel_changed_points_sam_at_the_change(ctx, scene):
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    await start(ctx, image, mask)
    out = await analyze_frame(ctx, 180.0, image, segment=True)
    [(concept, prompts)] = ctx.segmenter.pointed_asks
    x0, y0, _, _ = roi_box(ctx.vessels[0], *image.shape[:2], margin=CROP_MARGIN_PX)
    ys, xs = np.nonzero(mask)
    bx0, by0, bx1, by1 = prompts[0].box
    assert concept == "root" and len(prompts) == 1 and prompts[0].point is not None
    assert bx0 + x0 <= xs.min() and by0 + y0 <= ys.min() and bx1 + x0 >= xs.max() and by1 + y0 >= ys.max()
    assert drawn_by(ctx, out.frame_id) == ["sam-3.1/pointed"]
    assert via_of_a(ctx, 180.0) == "pointed"
    reading = last_length_of_a(ctx)
    assert reading.t == 180.0 and reading.value > 30


@pytest.mark.anyio
async def test_when_pointed_sam_finds_nothing_code_outlines_the_change(ctx, scene):
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    ctx.segmenter.pointed_steps = ["empty"]
    await start(ctx, image, mask)
    out = await analyze_frame(ctx, 180.0, image, segment=True)
    assert drawn_by(ctx, out.frame_id) == ["change-map"]
    assert via_of_a(ctx, 180.0) == "code"
    reading = last_length_of_a(ctx)
    assert reading.t == 180.0 and reading.value > 30


@pytest.mark.anyio
async def test_a_vessel_sized_answer_is_dropped_for_the_code_outline(ctx, scene):
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    ctx.segmenter.pointed_steps = ["whole"]
    await start(ctx, image, mask)
    out = await analyze_frame(ctx, 180.0, image, segment=True)
    assert drawn_by(ctx, out.frame_id) == ["change-map"]


@pytest.mark.anyio
async def test_a_sam_outline_far_bigger_than_the_change_is_replaced_by_the_change(ctx, scene):
    """Pointed at a swarm in a square region around a round dish, SAM sometimes outlines the whole dish: under the
    vessel-sized guard (a disc covers ~80% of its square), but many times the change it was pointed at (D-92)."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    ctx.segmenter.pointed_steps = ["spill"]
    await start(ctx, image, mask)
    out = await analyze_frame(ctx, 180.0, image, segment=True)
    assert drawn_by(ctx, out.frame_id) == ["change-map"]


@pytest.mark.anyio
async def test_a_vessel_that_changed_all_over_is_neither_pointed_at_nor_outlined(ctx, scene):
    """Light, a fogged lid or drying agar change the whole vessel at once: not growth, and nothing to point at."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    await start(ctx, image, mask)
    shaded = plain(image, mask).astype(np.int16)
    shaded[roi_mask(ctx.vessels[0], *image.shape[:2])] -= 40  # inside the vessel only
    out = await analyze_frame(ctx, 180.0, np.clip(shaded, 0, 255).astype(np.uint8), segment=True)
    assert ctx.segmenter.pointed_asks == [] and drawn_by(ctx, out.frame_id) == []


@pytest.mark.anyio
async def test_after_a_move_past_a_sighting_the_start_is_not_taken_again(ctx, scene):
    """A start taken after the object was seen already holds it: the change would be only the growth since the move.
    So once the vessel has moved past a sighting, SAM isn't pointed there again; a miss stays a gap (D-90)."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["ok"] * 4 + ["empty"])
    await start(ctx, image, mask)
    await analyze_frame(ctx, 180.0, image, segment=True)  # found by name
    a = ctx.vessels[0]
    ctx.vessels = [a.model_copy(update={"roi": [(x + 5, y) for x, y in a.roi]}), *ctx.vessels[1:]]
    for t in (240.0, 300.0, 360.0):
        await analyze_frame(ctx, t, plain(image, mask), segment=True)
    await analyze_frame(ctx, 420.0, image, segment=True)
    assert ctx.segmenter.pointed_asks == []


@pytest.mark.anyio
async def test_a_code_outline_alone_is_not_a_sighting(ctx, scene):
    """Code outlined a change SAM never confirmed (a bubble, condensation): a later empty answer where nothing has
    changed is still a zero, not a miss of something SAM never found (D-90)."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty", "empty"])
    ctx.segmenter.pointed_steps = ["empty"]
    await start(ctx, image, mask)
    coded = await analyze_frame(ctx, 180.0, image, segment=True)
    assert drawn_by(ctx, coded.frame_id) == ["change-map"]
    await analyze_frame(ctx, 240.0, plain(image, mask), segment=True)
    reading = last_length_of_a(ctx)
    assert (reading.t, reading.value) == (240.0, 0.0) and misses(ctx) == []


@pytest.mark.anyio
async def test_beside_an_outline_sam_kept_a_change_it_would_not_keep_to_is_left_out(ctx, scene):
    """Code outlines only a vessel where SAM kept nothing: beside a swarm SAM traced, the changes it wouldn't keep to
    were mostly the rim or bands of agar (D-92, 45 of 66 code patches on the swarming re-import)."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty"])
    ctx.segmenter.pointed_steps = ["bloat-second"]
    await start(ctx, image, mask)
    grown = image.copy()
    x0, y0 = (int(min(c)) for c in zip(*ctx.vessels[0].roi, strict=True))
    grown[y0 + 10 : y0 + 22, x0 + 10 : x0 + 25] = 30  # a second change, away from the root
    out = await analyze_frame(ctx, 180.0, grown, segment=True)
    [(_, prompts)] = ctx.segmenter.pointed_asks
    assert len(prompts) == 2
    assert drawn_by(ctx, out.frame_id) == ["sam-3.1/pointed"]


@pytest.mark.anyio
async def test_sixteen_pointed_objects_are_not_sams_object_limit(ctx, scene):
    """SAM traces at most 16 prompted objects because Argus sends at most 16 boxes: no "there may be more" warning."""
    image, _ = scene

    class Sixteen(FakeSegmenter):
        async def pointed(self, image_bgr, concept, prompts):
            patch = MaskPatch(0, 0, np.ones((2, 2), bool))
            return SegmentResult(
                [Track(f"obj{i}", concept, (TrackFrame(0, patch, 0.9),)) for i in range(1, 17)], call()
            )

    ctx.segmenter = Sixteen()
    await segment_with_retries(ctx, image, "root", t=0.0, prompts=[ObjectPrompt((0, 0, 1, 1))] * 16)
    assert "quality" not in kinds(ctx)


@pytest.mark.anyio
async def test_no_change_means_no_pointed_call(ctx, scene):
    """Found by name, then lost where nothing changed since the start: a miss (D-90), and SAM isn't asked again."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["ok", "empty"])
    await start(ctx, image, mask)
    await analyze_frame(ctx, 180.0, image, segment=True)
    await analyze_frame(ctx, 240.0, plain(image, mask), segment=True)
    assert ctx.segmenter.pointed_asks == []
    assert last_length_of_a(ctx).t == 180.0
    assert len(misses(ctx)) == 1


@pytest.mark.anyio
async def test_a_concept_that_does_not_appear_is_never_pointed(ctx, scene):
    image, mask = scene
    appearing(ctx, "stem")
    ctx.segmenter.script(["ok"] * 6 + ["empty", "empty"])
    await start(ctx, image, mask)
    await analyze_frame(ctx, 180.0, image, segment=True)
    assert [concept for concept, _ in ctx.segmenter.pointed_asks] == ["root"]


@pytest.mark.anyio
async def test_a_refused_or_failed_pointed_call_still_outlines_the_change(ctx, scene):
    """The change is code and costs nothing: when the spend cap refuses SAM, or SAM fails, code outlines it."""
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty", "empty"])
    await start(ctx, image, mask)
    ctx.settings = ctx.settings.model_copy(update={"run_spend_cap_usd": 0.0101})  # by name fits, pointed doesn't
    refused = await analyze_frame(ctx, 180.0, image, segment=True)
    assert ctx.segmenter.pointed_asks == [] and drawn_by(ctx, refused.frame_id) == ["change-map"]
    ctx.settings = ctx.settings.model_copy(update={"run_spend_cap_usd": 10.0})
    ctx.segmenter.pointed_steps = ["fail"] * 3
    failed = await analyze_frame(ctx, 240.0, image, segment=True)
    assert len(ctx.segmenter.pointed_asks) == 3 and drawn_by(ctx, failed.frame_id) == ["change-map"]
    assert "segment_failed" in kinds(ctx)


@pytest.mark.anyio
async def test_the_reference_starts_again_after_the_vessel_moves(ctx, scene):
    image, mask = scene
    appearing(ctx)
    ctx.segmenter.script(["ok"] * 3 + ["empty", "ok", "ok", "empty"])
    await start(ctx, image, mask)
    a = ctx.vessels[0]
    ctx.vessels = [a.model_copy(update={"roi": [(x + 5, y) for x, y in a.roi]}), *ctx.vessels[1:]]
    await analyze_frame(ctx, 180.0, image, segment=True)  # the first frame of the new reference
    for t in (240.0, 300.0):
        await analyze_frame(ctx, t, plain(image, mask), segment=True)
    assert ctx.segmenter.pointed_asks == []
    await analyze_frame(ctx, 360.0, image, segment=True)
    assert len(ctx.segmenter.pointed_asks) == 1
