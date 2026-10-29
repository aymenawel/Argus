"""The import pipeline on a synthetic clip: a card and a bar that grows in vessel A. Fake segmenter, no network."""

import asyncio

import cv2
import numpy as np
import pytest
from pydantic import SecretStr

import argus.pipeline.jobs as jobs_module
from argus.api.events import EventBroker
from argus.calibration.card import STANDARD
from argus.config import Settings
from argus.domain import ModelCallDraft, Role, RunMode, RunSource, RunStatus, SourceKind, VesselDraft
from argus.pipeline.analyzer import RunContext
from argus.pipeline.imported import ImportRequest, run_import
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.recipes.model import Recipe
from argus.segment import MaskPatch, SegmentError, SegmentResult, Track, TrackFrame
from argus.storage.files import RunFiles
from argus.storage.repos import add_vessels, create_run, events_for_run, frames_for_run, get_run, measurements_for_run
from tests.helpers import on_a_bench, scene_with_bar_on_card_plane

FPS, FRAMES, SCALE = 10, 120, 60  # 12 s of video = 12 run minutes
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


def ok_call(frames=0, images=0):
    cost = 0.0025 * images + 0.0002 * max(frames, 50) * (frames > 0)
    return ModelCallDraft(
        function="segment",
        model="sam-3.1",
        tier="segment",
        images=images,
        frames=frames,
        cost_usd=cost,
        latency_s=0.1,
        status="ok",
    )


def dark_patches(image_bgr):
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    count, labels, stats, _ = cv2.connectedComponentsWithStats((grey < 60).astype(np.uint8))
    patches = []
    for i in range(1, count):
        x, y, w, h = (
            int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT)
        )
        if w * h >= 20:
            patches.append(MaskPatch(x, y, labels[y : y + h, x : x + w] == i))
    return patches


class FakeSegmenter:
    def __init__(self, video_fails=False):
        self.video_fails, self.modes = video_fails, []

    async def image(self, image_bgr, concept):
        self.modes.append("image")
        tracks = [Track(f"obj{i}", concept, (TrackFrame(0, p, 0.9),)) for i, p in enumerate(dark_patches(image_bgr))]
        return SegmentResult(tracks, ok_call(images=1))

    async def video(self, clip, concept):
        self.modes.append("video")
        if self.video_fails:
            raise SegmentError(
                "APIError: 500",
                ModelCallDraft(
                    function="segment",
                    model="sam-3.1",
                    tier="segment",
                    frames=50,
                    cost_usd=0.0,
                    latency_s=0.1,
                    status="error",
                    error="APIError: 500",
                ),
            )
        capture = cv2.VideoCapture(str(clip.path))
        by_object: dict[int, list[TrackFrame]] = {}
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            for j, patch in enumerate(dark_patches(frame)):
                by_object.setdefault(j, []).append(TrackFrame(index, patch, 0.9))
            index += 1
        capture.release()
        assert index == clip.frame_count
        tracks = [Track(f"obj{j}", concept, tuple(frames)) for j, frames in by_object.items()]
        return SegmentResult(tracks, ok_call(frames=clip.frame_count))


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "jars é" / "run 1.mp4"
    path.parent.mkdir()
    writer = None
    for i in range(FRAMES):
        image, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=10 + 30 * i / (FRAMES - 1), width_mm=2)
        if writer is None:
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, image.shape[1::-1])
        writer.write(image)
    writer.release()
    return path


@pytest.fixture
def ctx(db, exp, tmp_path):
    _, full = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)
    ys, xs = np.nonzero(full)
    a = [
        (xs.min() - 40, ys.min() - 40),
        (xs.max() + 40, ys.min() - 40),
        (xs.max() + 40, ys.max() + 40),
        (xs.min() - 40, ys.max() + 40),
    ]
    b = [(x, y + 300) for x, y in a]
    run = create_run(
        db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.VIDEO, paths=["run 1.mp4"]), time_scale=SCALE
    )
    vessels = add_vessels(
        db,
        run.id,
        [
            VesselDraft(label="A", role=Role.TREATMENT, roi=[(float(x), float(y)) for x, y in a]),
            VesselDraft(label="B", role=Role.CONTROL, roi=[(float(x), float(y)) for x, y in b]),
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
    )
    context.retry_delays_s = (0.0, 0.0)
    return context


def request(clip):
    return ImportRequest(paths=[clip], time_scale=SCALE)


def lengths_of_a(ctx):
    a = ctx.vessels[0].id
    return [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == a]


@pytest.mark.anyio
async def test_import_measures_growth_at_the_analysis_step(ctx, clip):
    status = await run_import(ctx, request(clip), cancel=asyncio.Event())
    rows = lengths_of_a(ctx)
    assert status is RunStatus.FINISHED and get_run(ctx.db, ctx.run.id).status is RunStatus.FINISHED
    assert len(rows) >= 10 and rows[-1].value > rows[0].value + 20
    # Each reading's ± (which includes the skeleton's end effect) holds the bar's true length at that moment.
    for row in rows:
        true_mm = 10 + 30 * (row.t / SCALE * FPS) / (FRAMES - 1)
        assert abs(row.value - true_mm) <= row.uncertainty, (row.t, row.value, true_mm)
    change_times = {e.t_start for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "change"}
    on_grid = [f.t % 60 < 6.5 or f.t % 60 > 53.5 or f.t in change_times for f in frames_for_run(ctx.db, ctx.run.id)]
    assert all(on_grid) and all(f.analyzed for f in frames_for_run(ctx.db, ctx.run.id))
    assert ctx.segmenter.modes == ["video", "video"]  # one clip per vessel
    progress = [e.data for e in ctx.broker.since(0) if e.type == "run_progress"]
    assert {p["stage"] for p in progress} == {"scan", "segment", "measure"}
    assert [e.data["status"] for e in ctx.broker.since(0) if e.type == "run_status"] == ["finished"]


@pytest.mark.anyio
async def test_video_mode_failure_falls_back_to_image_mode(ctx, clip):
    ctx.segmenter = FakeSegmenter(video_fails=True)
    status = await run_import(ctx, request(clip), cancel=asyncio.Event())
    assert status is RunStatus.FINISHED and len(lengths_of_a(ctx)) >= 10
    assert ctx.segmenter.modes.count("video") == 6 and "image" in ctx.segmenter.modes  # 3 attempts x 2 vessels
    with ctx.db.read() as c:
        statuses = [r["status"] for r in c.execute("SELECT status FROM model_calls WHERE run_id=?", (ctx.run.id,))]
    assert statuses.count("error") == 6 and statuses.count("ok") >= 10


@pytest.mark.anyio
async def test_cancel_stops_the_run(ctx, clip):
    cancel = asyncio.Event()
    cancel.set()
    assert await run_import(ctx, request(clip), cancel=cancel) is RunStatus.STOPPED
    assert get_run(ctx.db, ctx.run.id).status is RunStatus.STOPPED


@pytest.mark.anyio
async def test_crop_clips_are_h264_for_sam(ctx, clip):
    await run_import(ctx, request(clip), cancel=asyncio.Event())
    crop = ctx.files.crop_path("A", "root")
    capture = cv2.VideoCapture(str(crop))
    fourcc = int(capture.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little").decode("ascii", "replace").lower()
    capture.release()
    assert crop.is_file() and fourcc in {"avc1", "h264"}


@pytest.fixture
def dimmed_clip(tmp_path):
    """The growing bar, with the lamp dimmed to 70 % halfway through."""
    path = tmp_path / "dimmed.mp4"
    writer = None
    for i in range(FRAMES):
        image, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=10 + 30 * i / (FRAMES - 1), width_mm=2)
        if i >= FRAMES // 2:
            image = (image.astype(np.float32) * 0.7).astype(np.uint8)
        if writer is None:
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, image.shape[1::-1])
        writer.write(image)
    writer.release()
    return path


@pytest.mark.anyio
async def test_a_lamp_change_does_not_stop_the_import_measuring(ctx, dimmed_clip):
    await run_import(ctx, request(dimmed_clip), cancel=asyncio.Event())
    rows = lengths_of_a(ctx)
    assert rows and rows[-1].t >= SCALE * (FRAMES - 1) / FPS - ctx.recipe.analysis_step_s
    assert not [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "intervention"]


@pytest.mark.anyio
async def test_stop_during_the_segment_stage_stops_sam_calls(ctx, clip):
    cancel = asyncio.Event()

    class StopsAfterTwoImages(FakeSegmenter):
        async def image(self, image_bgr, concept):
            if self.modes.count("image") == 2:
                cancel.set()
            return await super().image(image_bgr, concept)

    ctx.segmenter = StopsAfterTwoImages(video_fails=True)
    assert await run_import(ctx, request(clip), cancel=cancel) is RunStatus.STOPPED
    assert ctx.segmenter.modes.count("image") <= 4  # the calls in flight finish; no new ones start
    assert [e.data["status"] for e in ctx.broker.since(0) if e.type == "run_status"] == ["stopped"]


@pytest.mark.anyio
async def test_a_forced_stop_tells_the_page_and_logs_the_call_in_flight(ctx, clip, monkeypatch):
    class Hangs(FakeSegmenter):
        async def video(self, clip, concept):
            self.modes.append("video")
            await asyncio.sleep(3600)  # a stalled SAM stream

    monkeypatch.setattr(jobs_module, "STOP_WAIT_S", 0.2)
    jobs = RunJobs(ctx.db, ctx.broker, ctx.settings, {"seed-germination": RECIPE}, CameraHub(), segmenter=Hangs())
    jobs.start_import(ctx.run, ctx.vessels, request(clip))
    while "video" not in jobs.segmenter.modes:
        await asyncio.sleep(0.05)
    assert await jobs.stop(ctx.run.id)
    assert get_run(ctx.db, ctx.run.id).status is RunStatus.STOPPED
    assert [e.data["status"] for e in ctx.broker.since(0) if e.type == "run_status"] == ["stopped"]
    with ctx.db.read() as c:
        errors = [r["error"] for r in c.execute("SELECT error FROM model_calls WHERE run_id=?", (ctx.run.id,))]
    assert errors and all(e == "cancelled" for e in errors)


@pytest.fixture
def bumped_clip(tmp_path):
    """The growing bar on a textured bench; the camera is knocked (everything shifts) halfway through."""
    path = tmp_path / "bumped.mp4"
    writer = None
    for i in range(FRAMES):
        image, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=10 + 30 * i / (FRAMES - 1), width_mm=2)
        image = on_a_bench(image)
        if i >= FRAMES // 2:
            image = np.roll(image, (30, 40), axis=(0, 1))
        if writer is None:
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, image.shape[1::-1])
        writer.write(image)
    writer.release()
    return path


@pytest.mark.anyio
async def test_after_a_camera_move_the_import_measures_where_the_vessels_went(ctx, bumped_clip):
    drawn = np.asarray(ctx.vessels[0].roi)
    await run_import(ctx, request(bumped_clip), cancel=asyncio.Event())
    [moved] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "camera_moved"]
    assert np.allclose(np.asarray(moved.detail["rois"][ctx.vessels[0].id]) - drawn, (40, 30), atol=3)
    after = [m for m in lengths_of_a(ctx) if m.t >= moved.t_start]
    assert after  # still measured after the bump, and true: no false zeros from regions left behind
    for row in after:
        true_mm = 10 + 30 * (row.t / SCALE * FPS) / (FRAMES - 1)
        assert abs(row.value - true_mm) <= row.uncertainty, (row.t, row.value, true_mm)


@pytest.mark.anyio
async def test_the_image_fallback_is_one_full_frame_call_per_sample_for_every_vessel(ctx, clip):
    ctx.segmenter = FakeSegmenter(video_fails=True)
    await run_import(ctx, request(clip), cancel=asyncio.Event())
    samples = frames_for_run(ctx.db, ctx.run.id)
    assert ctx.segmenter.modes.count("image") == len(samples)  # not one per vessel: SAM sees the whole frame
    for row in lengths_of_a(ctx):
        true_mm = 10 + 30 * (row.t / SCALE * FPS) / (FRAMES - 1)
        assert abs(row.value - true_mm) <= row.uncertainty, (row.t, row.value, true_mm)


@pytest.mark.anyio
async def test_a_hand_beside_a_vessel_in_a_recording_is_logged_and_skipped(ctx, tmp_path):
    xs, ys = zip(*ctx.vessels[0].roi, strict=True)
    path = tmp_path / "hand.mp4"
    writer = None
    for i in range(FRAMES):
        image, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=10 + 30 * i / (FRAMES - 1), width_mm=2)
        if 50 <= i < 60:  # the sample at 5 s of video (300 s of run time); a hand doesn't stay put for a minute
            image[int(min(ys)) : int(max(ys)), int(max(xs)) + 2 : int(max(xs)) + 60] = (60, 90, 140)
        if writer is None:
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, image.shape[1::-1])
        writer.write(image)
    writer.release()
    await run_import(ctx, request(path), cancel=asyncio.Event())
    hands = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "intervention"]
    assert [(e.vessel_id, e.t_start) for e in hands] == [(ctx.vessels[0].id, 300.0)]
    times = {m.t for m in lengths_of_a(ctx)}
    assert 300.0 not in times and {240.0, 360.0} <= times
