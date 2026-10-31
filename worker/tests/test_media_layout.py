"""Where the timelapse puts each source frame in time, and the words it draws (D-85): all from stored records."""

import re
from datetime import UTC, datetime

import pytest

from argus.config import REPO_ROOT
from argus.domain import Note
from argus.media.layout import PALETTE, axis_time, caption_at, clock_text, condition_groups, schedule, segments


def note(t: float, author: str, body: dict) -> Note:
    return Note(
        id=f"note{t}",
        run_id="run",
        t=t,
        author=author,
        level="checkpoint" if author == "ai" else None,
        tag=None if author == "ai" else "intervention",
        body=body,
        refs=[],
        evidence=[],
        check_status="passed" if author == "ai" else "researcher",
        model_call_id=None,
    )


def test_schedule_covers_the_run_in_the_chosen_length():
    ts = [i * 1800.0 for i in range(95)]  # 47 h
    slots = schedule(ts, 20.0)
    assert len(slots) == 600 and slots[0].t == 0.0 and slots[-1].t == ts[-1]


def test_each_slot_shows_the_frame_at_or_before_its_t():
    ts = [0.0, 10.0, 100.0, 1000.0]
    slots = schedule(ts, 1.0, fps=10)
    assert all(ts[s.a] <= s.t for s in slots) and slots[-1].a == 3


def test_cross_fade_holds_then_dissolves():
    slots = schedule([0.0, 100.0], 10 / 30, fps=30)  # 10 slots across one gap
    weights = [round(s.w, 2) for s in slots[:-1]]
    assert weights[:5] == [0.0] * 5 and weights[-1] > 0.75 and weights == sorted(weights)


def test_dense_frames_never_cross_fade():
    assert all(s.w == 0.0 for s in schedule([i * 1.0 for i in range(3000)], 2.0))


def test_a_window_schedules_only_its_part_of_the_run():
    slots = schedule([i * 10.0 for i in range(100)], 1.0, fps=10, t_from=200.0, t_to=290.0)
    assert slots[0].t == 200.0 and slots[-1].t == 290.0 and slots[0].a == 20 and slots[-1].a == 29


def test_a_single_frame_run_makes_a_still():
    slots = schedule([5.0], 2.0)
    assert len(slots) == 60 and all(s.a == 0 and s.b is None and s.t == 5.0 for s in slots)
    assert len(schedule([5.0, 5.0, 5.0], 2.0)) == 60


def test_gaps_in_readings_stay_gaps():
    points = [(0, 1), (60, 2), (120, 3), (3600, 4), (3660, 5)]
    assert [len(s) for s in segments(points)] == [3, 2]
    assert segments([]) == [] and segments([(0, 1)]) == [[(0, 1)]]


@pytest.mark.parametrize(
    "t, start, text",
    [
        (84600.0, None, "t 23.5 h"),
        (1500.0, None, "t 25 min"),
        (1500.0, datetime(2026, 11, 2, 14, 0, tzinfo=UTC), "t 25 min · 14:25"),
    ],
)
def test_clock_text(t, start, text):
    assert clock_text(t, start) == text


def test_the_caption_is_the_stored_note_in_effect():
    notes = [note(10, "ai", {"observation": "Glass B darkened."}), note(50, "researcher", {"text": "Dye added"})]
    assert caption_at(notes, 5) is None
    assert caption_at(notes, 20) == "Glass B darkened."
    assert caption_at(notes, 60) == "Dye added"


def test_the_palette_matches_the_web_tokens():
    css = (REPO_ROOT / "web" / "styles" / "tokens.css").read_text(encoding="utf-8")
    dark = css[css.index(':root[data-theme="dark"]') :]
    dark = dark[: dark.index("}")]
    tokens = dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-f]{6})", dark))
    assert {k: tokens[f"--{k}"] for k in ("ground", "text", "muted", "accent")} == PALETTE


@pytest.mark.parametrize(
    "t, span, text",
    [
        (0.0, 169200.0, "0 h"),
        (169200.0, 169200.0, "47 h"),
        (4320.0, 7200.0, "1.2 h"),
        (0.0, 1500.0, "0 min"),
        (1500.0, 1500.0, "25 min"),
    ],
)
def test_axis_times_share_one_unit(t, span, text):
    assert axis_time(t, span) == text


def test_condition_labels_read_like_the_results_legend():
    vessels = [
        {"role": "treatment", "condition": {"factor": "temperature", "value": 40.0, "unit": "°C"}},
        {"role": "control", "condition": None},
        {"role": "treatment", "condition": {"factor": "salt", "value": 2.5, "unit": "g/L"}},
    ]
    assert [g.label for g in condition_groups(vessels).values()] == ["Control", "Treatment: 40", "Treatment: 2.5"]
