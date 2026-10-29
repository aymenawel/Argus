"""Live runs from a list of prepared frames with a fake clock (0.5 s per frame). Fake segmenter, no camera."""

import asyncio
import time

import numpy as np
import pytest
from pydantic import SecretStr

from argus.api.events import EventBroker
from argus.calibration.card import STANDARD
from argus.capture.quality import DEFAULT_THRESHOLDS, QualityThresholds
from argus.config import Settings
from argus.domain import EventKind, Role, RunMode, RunSource, RunStatus, SourceKind, VesselDraft
from argus.pipeline.analyzer import RunContext
from argus.pipeline.live import CameraHub, run_live
from argus.recipes.model import Recipe, WatcherSpec
from argus.storage.files import RunFiles
from argus.storage.repos import add_vessels, create_run, events_for_run, frames_for_run, get_run, measurements_for_run
from argus.watcher import Watcher, WatcherSettings
from tests.helpers import CARD_AREA, on_a_bench, scene_with_bar_on_card_plane
from tests.test_analyzer import FakeSegmenter

DT = 0.5


def recipe(mode: str, step: float) -> Recipe:
    return Recipe.model_validate(
        {
            "id": "test",
            "version": 1,
            "title": "Test",
            "default_mode": mode,
            "analysis_step_s": step,
            "curve": "linear",
            "concepts": [{"name": "root"}],
            "measurements": [
                {"id": "length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"},
                {"id": "colour", "family": "colour", "method": "lab_mean", "from": "root", "unit": "Lab"},
            ],
            "main_measurement": "length",
        }
    )


SHORT, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=20, width_mm=2)
LONG, LONG_MASK = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)


class ListSource:
    """Hands out frames in order; each read moves the fake clock on by DT."""

    def __init__(self, frames, clock, on_read=None):
        self.frames, self.clock, self.on_read, self.closed = list(frames), clock, on_read, False

    def read(self):
        if not self.frames:
            return None
        self.clock.now += DT
        if self.on_read:
            self.on_read(self.clock.now)
        return self.frames.pop(0)

    def close(self):
        self.closed = True


class Clock:
    def __init__(self):
        self.now = -DT  # the first read lands on t = 0

    def __call__(self):
        return self.now


async def no_sleep(_):
    await asyncio.sleep(0)


@pytest.fixture
def make_ctx(db, exp, tmp_path):
    def make(mode="smart_trigger", step=5.0, segment_interval_s=10.0):
        ys, xs = np.nonzero(LONG_MASK)
        a = [
            (xs.min() - 40, ys.min() - 40),
            (xs.max() + 40, ys.min() - 40),
            (xs.max() + 40, ys.max() + 40),
            (xs.min() - 40, ys.max() + 40),
        ]
        run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
        vessels = add_vessels(
            db, run.id, [VesselDraft(label="A", role=Role.TREATMENT, roi=[(float(x), float(y)) for x, y in a])]
        )
        settings = Settings(
            model_api_key=SecretStr("k"), data_dir=tmp_path / "data", segment_interval_s=segment_interval_s
        )
        rec = recipe(mode, step)
        ctx = RunContext(
            db=db,
            broker=EventBroker(),
            settings=settings,
            files=RunFiles(settings.data_dir, exp.id, run.id),
            recipe=rec,
            run=run,
            vessels=vessels,
            segmenter=FakeSegmenter(),
        )
        ctx.retry_delays_s = (0.0, 0.0)
        watcher = Watcher(vessels, rec.watcher, WatcherSettings.from_recipe(rec))
        return ctx, watcher

    return make


async def live(ctx, watcher, frames, *, cancel=None, on_read=None, quality=DEFAULT_THRESHOLDS):
    clock = Clock()
    source = ListSource(frames, clock, on_read)
    status = await run_live(
        ctx, source, watcher, cancel=cancel or asyncio.Event(), clock=clock, sleep=no_sleep, quality=quality
    )
    return status, source


def model_calls(ctx):
    with ctx.db.read() as c:
        return c.execute("SELECT t FROM model_calls WHERE run_id=? ORDER BY t", (ctx.run.id,)).fetchall()


@pytest.mark.anyio
async def test_live_segments_on_change_and_measures_colour_every_step(make_ctx):
    ctx, watcher = make_ctx()
    frames = [SHORT] * 40 + [LONG] * 80  # 60 s; the bar grows at t = 20 s
    status, source = await live(ctx, watcher, frames)
    calls = [row["t"] for row in model_calls(ctx)]
    assert status is RunStatus.STOPPED and source.closed is False  # the caller owns the source
    assert len(calls) == 2 and calls[0] == 0.0 and 20.0 <= calls[1] <= 21.6  # first frame, then the change
    stored = [f.t for f in frames_for_run(ctx.db, ctx.run.id)]
    assert len(stored) >= 12 and all(t2 - t1 <= 5.0 + 1e-6 for t1, t2 in zip(stored, stored[1:], strict=False))
    colour_times = {m.t for m in measurements_for_run(ctx.db, ctx.run.id, metric="colour_l")}
    assert colour_times == set(stored)  # colour on every stored frame, from the newest masks
    lengths = measurements_for_run(ctx.db, ctx.run.id, metric="length")
    assert abs(lengths[0].value - 20) <= lengths[0].uncertainty and lengths[-1].value > 35


@pytest.mark.anyio
async def test_segmentation_never_runs_closer_than_the_interval(make_ctx):
    ctx, watcher = make_ctx(mode="continuous", step=1.0, segment_interval_s=10.0)
    await live(ctx, watcher, [SHORT] * 120)
    calls = [row["t"] for row in model_calls(ctx)]
    assert 5 <= len(calls) <= 7 and all(t2 - t1 >= 10.0 - 1e-6 for t1, t2 in zip(calls, calls[1:], strict=False))


@pytest.mark.anyio
async def test_a_hand_pauses_measuring_and_logs_an_intervention(make_ctx):
    ctx, watcher = make_ctx()
    hand = SHORT.copy()
    hand[:, :700] = 20  # an arm across the left of the scene, outside the vessel
    frames = [SHORT] * 20 + [hand] * 10 + [SHORT] * 20  # hand from 10 s to 15 s
    await live(ctx, watcher, frames)
    interventions = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "intervention"]
    assert len(interventions) == 1 and 9.99 <= interventions[0].t_start <= 10.5
    assert not [f for f in frames_for_run(ctx.db, ctx.run.id) if 9.99 <= f.t < 14.99]


@pytest.mark.anyio
async def test_stop_ends_the_run(make_ctx):
    ctx, watcher = make_ctx()
    cancel = asyncio.Event()
    status, _ = await live(
        ctx, watcher, [SHORT] * 120, cancel=cancel, on_read=lambda now: cancel.set() if now >= 2.0 else None
    )
    assert status is RunStatus.STOPPED and get_run(ctx.db, ctx.run.id).status is RunStatus.STOPPED
    assert max(f.t for f in frames_for_run(ctx.db, ctx.run.id)) <= 2.0


def test_the_camera_hub_shares_one_capture():
    opened = []

    class FakeCapture:
        def __init__(self):
            self.frame = np.full((48, 64, 3), 120, np.uint8)

        def read(self):
            return True, self.frame

        def release(self):
            opened.remove(self)

    def opener(index, settings):
        capture = FakeCapture()
        opened.append(capture)
        return capture, {}

    hub = CameraHub(opener=opener)
    first, _ = hub.acquire(0)
    second, _ = hub.acquire(0)
    assert len(opened) == 1
    for _ in range(200):
        if hub.latest_jpeg(0):
            break
        asyncio.run(asyncio.sleep(0.01))
    assert hub.latest_jpeg(0)[:2] == b"\xff\xd8" and first.read().shape == (48, 64, 3)
    first.close()
    assert len(opened) == 1
    second.close()
    assert opened == []


def test_a_camera_that_stops_delivering_ends_the_reads():
    class DyingCapture:
        def __init__(self):
            self.n = 0

        def read(self):
            self.n += 1
            return (True, np.full((48, 64, 3), self.n, np.uint8)) if self.n <= 5 else (False, None)

        def release(self):
            pass

    hub = CameraHub(opener=lambda index, settings: (DyingCapture(), {}), stale_after_s=0.3)
    source, _ = hub.acquire(0)
    started, seen = time.monotonic(), []
    for _ in range(10):
        frame = source.read()
        if frame is None:
            break
        seen.append(int(frame[0, 0, 0]))
    assert seen and seen == sorted(set(seen)) and seen[-1] == 5  # each frame once; the last is never reused
    assert time.monotonic() - started < 2.0
    assert hub.latest_jpeg(0) is None  # previews don't show a frozen frame as live either
    source.close()


@pytest.mark.anyio
async def test_a_lost_camera_ends_the_run_with_an_event(make_ctx):
    ctx, watcher = make_ctx()
    status, _ = await live(ctx, watcher, [SHORT] * 6)
    assert status is RunStatus.STOPPED
    lost = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind is EventKind.INTERRUPTED]
    assert len(lost) == 1 and lost[0].detail == {"reason": "camera_lost"} and lost[0].t_start == pytest.approx(2.5)


@pytest.mark.anyio
async def test_a_lamp_change_does_not_stop_measuring(make_ctx):
    ctx, watcher = make_ctx()
    dimmer = (SHORT.astype(np.float32) * 0.7).astype(np.uint8)
    await live(ctx, watcher, [SHORT] * 12 + [dimmer] * 12)
    assert max(f.t for f in frames_for_run(ctx.db, ctx.run.id)) >= 10.0
    assert not [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind is EventKind.INTERVENTION]


@pytest.mark.anyio
async def test_capture_continues_while_sam_works(make_ctx):
    ctx, watcher = make_ctx(step=1.0)
    released, reads = asyncio.Event(), []

    class AnswersLate(FakeSegmenter):
        async def image(self, image_bgr, concept):
            await released.wait()  # SAM answers only once the loop has read 8 more frames
            return await super().image(image_bgr, concept)

    ctx.segmenter = AnswersLate()

    def on_read(now):
        reads.append(now)
        if len(reads) == 9:
            released.set()

    await asyncio.wait_for(live(ctx, watcher, [SHORT] * 16, on_read=on_read), 30)
    frames = frames_for_run(ctx.db, ctx.run.id)
    assert {0.0, 1.0, 2.0, 3.0} <= {f.t for f in frames}  # stored while SAM was still busy with t = 0
    assert all(f.analyzed for f in frames) and measurements_for_run(ctx.db, ctx.run.id, metric="length")


def lengths_after(ctx, t):
    a = ctx.vessels[0].id
    return [m for m in measurements_for_run(ctx.db, ctx.run.id, metric="length") if m.vessel_id == a and m.t >= t]


@pytest.mark.anyio
async def test_after_a_camera_move_the_vessels_follow_the_card(make_ctx):
    ctx, watcher = make_ctx(step=1.0, segment_interval_s=1.0)
    drawn = np.asarray(ctx.vessels[0].roi)
    still = on_a_bench(SHORT)
    bumped = np.roll(still, (30, 40), axis=(0, 1))  # the camera was knocked: everything shifted
    await live(ctx, watcher, [still] * 6 + [bumped] * 16, quality=QualityThresholds(settle_s=2.0))
    [moved] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind is EventKind.CAMERA_MOVED]
    followed = np.asarray(moved.detail["rois"][ctx.vessels[0].id])
    assert np.allclose(followed - drawn, (40, 30), atol=3) and np.allclose(ctx.vessels[0].roi, followed)
    after = lengths_after(ctx, moved.t_start)
    assert after and all(abs(m.value - 20) <= m.uncertainty for m in after)  # the bar, not a false zero


@pytest.mark.anyio
async def test_a_moved_card_is_recalibrated_and_the_vessels_stay(make_ctx):
    ctx, watcher = make_ctx(step=1.0)
    drawn = list(ctx.vessels[0].roi)
    still = on_a_bench(SHORT)
    nudged = still.copy()
    nudged[CARD_AREA] = np.roll(still[CARD_AREA], (8, 12), axis=(0, 1))  # someone pushed the card; the jars stayed
    await live(ctx, watcher, [still] * 6 + [nudged] * 8)
    [moved] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind is EventKind.CAMERA_MOVED]
    assert moved.detail == {"message": "card moved: recalibrated"} and list(ctx.vessels[0].roi) == drawn
    with ctx.db.read() as c:
        assert c.execute("SELECT COUNT(*) FROM calibrations WHERE run_id=?", (ctx.run.id,)).fetchone()[0] == 2


@pytest.mark.anyio
async def test_a_segmentation_owed_before_the_card_is_seen_runs_once_it_is(make_ctx):
    ctx, _ = make_ctx()
    # Structure only: in these white scenes the card's arrival would shift the colour reference and fire a change.
    watcher = Watcher(ctx.vessels, WatcherSpec(signals=["ssim"]), WatcherSettings.from_recipe(ctx.recipe))
    with_card = on_a_bench(SHORT)  # textured, so frames without the card aren't rejected as featureless
    no_card = with_card.copy()
    no_card[CARD_AREA] = 255  # the card isn't in view yet
    await live(ctx, watcher, [no_card] * 4 + [with_card] * 6)
    assert model_calls(ctx)  # not an hour later, at the next check-in


@pytest.mark.anyio
async def test_a_hand_beside_a_vessel_pauses_that_vessel_and_is_logged(make_ctx):
    ctx, watcher = make_ctx(step=1.0)
    xs, ys = zip(*ctx.vessels[0].roi, strict=True)
    beside = SHORT.copy()
    beside[int(min(ys)) : int(max(ys)), int(max(xs)) + 2 : int(max(xs)) + 60] = (60, 90, 140)  # a hand by vessel A
    await live(ctx, watcher, [SHORT] * 6 + [beside] * 6 + [SHORT] * 6)
    [hand] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind is EventKind.INTERVENTION]
    assert hand.vessel_id == ctx.vessels[0].id and hand.t_start == pytest.approx(3.0)
    times = {m.t for m in measurements_for_run(ctx.db, ctx.run.id, metric="colour_l")}
    assert not any(3.0 <= t < 6.0 for t in times) and any(t >= 6.0 for t in times)  # a gap, then readings again
