"""The watcher on synthetic scenes: a seeded texture, two vessels, a coloured disc growing in vessel A."""

import cv2
import numpy as np
from skimage.metrics import structural_similarity

from argus.domain import Role, Vessel
from argus.recipes.model import WatcherSpec
from argus.watcher import Watcher, WatcherSettings

A = Vessel(id="ves_A", run_id="r", label="A", role=Role.TREATMENT, roi=[(120, 150), (280, 150), (280, 350), (120, 350)])
B = Vessel(id="ves_B", run_id="r", label="B", role=Role.CONTROL, roi=[(450, 150), (610, 150), (610, 350), (450, 350)])
SPEC = WatcherSpec()
_rng = np.random.default_rng(7)
BACKGROUND = cv2.GaussianBlur(_rng.integers(60, 120, (600, 800, 3), dtype=np.uint8), (5, 5), 1)


def scene_with_disc(r: float, colour=(40, 140, 50)) -> np.ndarray:
    image = BACKGROUND.copy()
    cv2.circle(image, (200 * 16, 250 * 16), int(r * 16), colour, -1, lineType=cv2.LINE_AA, shift=4)
    return image


def brighten(image: np.ndarray, gain: float) -> np.ndarray:
    return np.clip(image.astype(np.float64) * gain, 0, 255).astype(np.uint8)


def ssim_a(f1: np.ndarray, f2: np.ndarray) -> float:
    g1, g2 = (cv2.cvtColor(f[150:350, 120:280], cv2.COLOR_BGR2GRAY) for f in (f1, f2))
    return structural_similarity(g1, g2, data_range=255)


def watcher(mode="smart_trigger", **overrides) -> Watcher:
    settings = WatcherSettings(mode=mode, interval_s=overrides.pop("interval_s", 60.0), **overrides)
    return Watcher([A, B], SPEC, settings)


def run(w: Watcher, frames, *, dt: float = 60.0, analyze_on_trigger: bool = True):
    """Feed frames at dt-second steps; returns (t, trigger) pairs. Triggered frames count as analyzed."""
    out = []
    for i, frame in enumerate(frames):
        t = i * dt
        triggers = w.observe(t, frame)
        out += [(t, trig) for trig in triggers]
        if analyze_on_trigger and triggers:
            w.mark_analyzed(t, frame)
    return out


def test_slow_growth_triggers_once_it_adds_up():
    frames = [scene_with_disc(20 + i * 0.4) for i in range(60)]
    assert all(ssim_a(f1, f2) > 0.97 for f1, f2 in zip(frames, frames[1:], strict=False))  # frame to frame: still
    events = run(watcher(debounce=3, cooldown_s=0.0), frames)
    changes = [(t, trig) for t, trig in events if trig.reason == "change"]
    assert events[0][1].reason == "first"
    assert changes and all(trig.vessel_id == A.id for _, trig in changes)


def test_a_lamp_switch_does_not_trigger():
    still = scene_with_disc(20)
    frames = [still] * 10 + [brighten(still, 1.6)] * 20
    assert [trig.reason for _, trig in run(watcher(), frames)] == ["first"]


def test_a_one_frame_flash_is_debounced():
    frames = [scene_with_disc(20)] * 10 + [scene_with_disc(45)] + [scene_with_disc(20)] * 10
    assert [trig.reason for _, trig in run(watcher(debounce=3), frames)] == ["first"]


def test_no_second_change_inside_the_cooldown():
    frames = [scene_with_disc(20)] * 2 + [scene_with_disc(45)] * 10  # 10 s steps; changed from t = 20 s
    events = run(watcher(debounce=1, cooldown_s=60.0), frames, dt=10.0, analyze_on_trigger=False)
    change_times = [t for t, trig in events if trig.reason == "change"]
    assert change_times[:2] == [20.0, 80.0]


def test_a_quiet_vessel_gets_a_scheduled_checkin():
    frames = [scene_with_disc(20)] * 19  # every 10 min for 3 h
    events = run(watcher(checkin_s=3600.0), frames, dt=600.0)
    assert [(t, trig.reason) for t, trig in events] == [
        (0.0, "first"),
        (3600.0, "checkin"),
        (7200.0, "checkin"),
        (10800.0, "checkin"),
    ]


def test_continuous_ticks_at_the_interval():
    frames = [scene_with_disc(20)] * 21  # t = 0, 0.5, ... 10 s
    events = run(watcher("continuous", interval_s=2.0), frames, dt=0.5)
    assert [(t, trig.reason) for t, trig in events] == [(0.0, "first")] + [(float(t), "tick") for t in (2, 4, 6, 8, 10)]


def test_hybrid_ticks_while_active_then_settles():
    frames = [scene_with_disc(20)] * 10 + [scene_with_disc(45)] * 20  # 1 s steps; change at t = 10 s
    events = run(watcher("hybrid", interval_s=1.0, debounce=1, hybrid_active_s=5.0), frames, dt=1.0)
    reasons = [(t, trig.reason) for t, trig in events]
    assert reasons[0] == (0.0, "first") and (10.0, "change") in reasons
    ticks = [t for t, reason in reasons if reason == "tick"]
    assert ticks and min(ticks) > 10.0 and max(ticks) <= 15.0  # ticks only while active


def test_a_colour_change_triggers_on_colour_alone():
    w = Watcher([A, B], WatcherSpec(signals=["colour"]), WatcherSettings(mode="smart_trigger", interval_s=60.0))
    frames = [scene_with_disc(40)] * 3 + [scene_with_disc(40, colour=(160, 60, 40))] * 5  # same shape, new colour
    changes = [(t, trig) for t, trig in run(w, frames) if trig.reason == "change"]
    assert [trig.vessel_id for _, trig in changes] == [A.id] and changes[0][1].colour_shift > 1.5
