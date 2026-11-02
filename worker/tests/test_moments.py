"""The highlights reel (D-85): moments from stored records, cut to 30–60 s, captions only from stored text."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from argus.config import REPO_ROOT, load_settings
from argus.domain import Plan, Verdict, VerdictLevel
from argus.measure.uncertainty import format_duration
from argus.media.moments import (
    END_S,
    MIN_S,
    TITLE_S,
    Chapter,
    Moment,
    collect_moments,
    end_lines,
    plan_chapters,
    reel_pace,
    title_lines,
)
from argus.media.records import load_records
from argus.recipes.loader import load_all
from argus.storage import repos
from tests.records import DRAFT, finished_run


@pytest.fixture
def records(db, tmp_path):
    settings = load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data")})
    run = finished_run(db, tmp_path / "data")
    return load_records(db, settings, load_all(REPO_ROOT / "recipes"), run.id)


def m(kind: str, t: float) -> Moment:
    return Moment(t, kind, f"{kind} at {t}")


def verdict(records, checks: list[dict], explanation: str = "The glasses differ. More would follow.") -> Verdict:
    return Verdict(
        id="ver_1",
        run_id=records.run.id,
        t=records.frames[-1].t,
        provisional=False,
        allowed=[VerdictLevel.INCONCLUSIVE],
        checks=checks,
        verdict=VerdictLevel.INCONCLUSIVE,
        body={"explanation": explanation},
        draft={},
        critique=None,
        refs=[],
        model_call_ids=[],
        fell_back=False,
    )


def test_moments_come_only_from_stored_records(records):
    moments = collect_moments(records)
    assert ("intervention", "Dye added") in [(x.kind, x.caption) for x in moments]
    # The change on B has no note citing it: its caption names the vessel, nothing more.
    assert ("change", "Change detected: B") in [(x.kind, x.caption) for x in moments]
    stored = {e.detail.get("message") for e in records.events} | {n.body.get("text") for n in records.notes}
    for moment in moments:
        assert moment.caption in stored or moment.caption.startswith(("Change detected: ", "Sample ")), moment


def test_half_way_moments_name_the_median_vessel_of_each_condition(records):
    fit = next(v["fit"] for v in records.fits["vessels"] if v["label"] == "B")
    assert fit["ok"] and fit["reached"]
    value, uncertainty = fit["half_time_h"]
    half_way = [x for x in collect_moments(records) if x.kind == "half_way"]
    assert (
        Moment(value * 3600, "half_way", f"Sample B (Test: 40) got half-way in {format_duration(value, uncertainty)}")
        in half_way
    )


def test_no_half_way_moments_without_readings(db, tmp_path):
    settings = load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data")})
    run = finished_run(db, tmp_path / "data", readings=False)
    records = load_records(db, settings, load_all(REPO_ROOT / "recipes"), run.id)
    assert [x for x in collect_moments(records) if x.kind == "half_way"] == []


def test_the_checkpoint_is_the_verdicts_moment(records):
    judged = replace(records, verdict=verdict(records, []))
    assert Moment(judged.verdict.t, "checkpoint", "The glasses differ.") in collect_moments(judged)


def test_the_pace_shows_about_two_frames_per_second():
    assert reel_pace([0, 600, 1200, 1800]) == 1200.0 and reel_pace([5.0]) == 1.0 and reel_pace([0, 0.2, 0.4]) == 1.0


def test_close_moments_merge_into_one_chapter():
    chapters = plan_chapters([m("change", 1000), m("change", 1010)], 0, 72000, pace=600)
    assert len(chapters) == 1 and len(chapters[0].moments) == 2


def test_the_budget_drops_the_lowest_ranked_moments_first():
    moments = [m("intervention", 500)] + [m("change", 4000 * i) for i in range(1, 17)]  # 17 separate chapters
    chapters = plan_chapters(moments, 0, 72000, pace=600)
    total = TITLE_S + END_S + sum(c.seconds for c in chapters)
    kept = [x for c in chapters for x in c.moments]
    assert 30 <= total <= 60 and moments[0] in kept
    assert [x.t for x in kept if x.kind == "change"] == [4000 * i for i in range(1, 10)]  # the latest went first


def test_a_short_reel_slows_down_to_thirty_seconds():
    chapters = plan_chapters([m("intervention", 36000)], 0, 72000, pace=600)
    assert TITLE_S + END_S + sum(c.seconds for c in chapters) == pytest.approx(MIN_S)


def test_a_run_without_moments_gets_one_chapter_of_the_whole_run():
    assert plan_chapters([], 0, 72000, pace=600) == [Chapter(0, 72000, MIN_S - TITLE_S - END_S, [])]


def test_title_and_end_cards(records):
    assert title_lines(records) == ["Dye in warm and room water", "No plan was locked for this run"]
    assert end_lines(records) == ["No verdict yet"]
    plan = Plan(
        **DRAFT.model_dump(),
        experiment_id=records.experiment.id,
        version=1,
        locked_at=datetime(2026, 11, 2, 9, tzinfo=UTC),
    )
    checks = [
        {"id": "a", "ok": True, "text": "A check that passed."},
        {"id": "b", "ok": None, "text": "A check still open."},
        {"id": "c", "ok": False, "text": "A check that failed."},
    ]
    judged = replace(records, plan=plan, verdict=verdict(records, checks))
    assert title_lines(judged) == [
        "Dye in warm and room water",
        f"Hypothesis: {DRAFT.hypothesis}",
        f"Prediction: {DRAFT.prediction}",
        "Plan locked Nov 2, 2026",
    ]
    assert end_lines(judged) == ["Verdict: Unclear", "A check that failed."]
    open_only = replace(records, verdict=verdict(records, checks[:2]))
    assert end_lines(open_only) == ["Verdict: Unclear", "A check still open."]


def test_a_hand_in_view_is_a_quality_moment(db, records):
    """The quality check logs a hand by the vessels as an intervention with flags, not words."""
    hand = repos.add_event(
        db,
        records.run.id,
        vessel_id=None,
        t_start=3000.0,
        kind="intervention",
        source="quality",
        detail={"flags": ["occluded"]},
    )
    moments = collect_moments(replace(records, events=[*records.events, hand]))
    assert Moment(3000.0, "quality", "Hand in view") in moments
    assert not any(x.kind == "intervention" and x.t == 3000.0 for x in moments)


def test_a_run_with_no_time_span_still_plays_thirty_seconds():
    """One frame, or every frame at the same t: the chapter is a still held long enough (review, Important 1)."""
    chapters = plan_chapters([m("intervention", 0)], 0, 0, pace=1.0)
    assert TITLE_S + END_S + sum(c.seconds for c in chapters) == pytest.approx(MIN_S)


def test_a_moment_after_the_last_frame_is_held_at_the_end():
    chapters = plan_chapters([m("intervention", 1800 + 5 * 600)], 0, 1800, pace=600)
    assert all(c.seconds > 0 and c.t_from <= c.t_to <= 1800 for c in chapters)
    assert TITLE_S + END_S + sum(c.seconds for c in chapters) == pytest.approx(MIN_S)
