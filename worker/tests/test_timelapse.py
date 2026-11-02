"""The timelapse (D-84, D-85): a finished run in seconds, its curves drawn over it, from stored records only."""

import json

import pytest

from argus.analyze.fits import fits_view
from argus.config import REPO_ROOT, load_settings
from argus.domain import RunMode, RunSource, RunStatus, SourceKind
from argus.media import MediaRefused
from argus.media.draw import Drawer
from argus.media.layout import chart_note, schedule
from argus.media.make import make_reel, make_timelapse
from argus.media.records import load_records
from argus.recipes.loader import load_all
from argus.storage import repos
from argus.storage.files import RunFiles
from tests.api_client import api_client, logged_functions
from tests.probe import ffprobe
from tests.records import finished_run


@pytest.fixture
def settings(tmp_path):
    return load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data")})


@pytest.fixture
def recipes():
    return load_all(REPO_ROOT / "recipes")


def test_fits_view_matches_the_route(db, tmp_path, recipes):
    run = finished_run(db, tmp_path / "data")
    with api_client(db, tmp_path) as client:
        as_json = json.loads(json.dumps(fits_view(db, recipes, run.id)))  # the route's tuples arrive as lists
        assert as_json == client.get(f"/api/runs/{run.id}/fits").json()
        as_json = json.loads(json.dumps(fits_view(db, recipes, run.id, "delta_e")))
        assert as_json == client.get(f"/api/runs/{run.id}/fits?metric=delta_e").json()


def test_fits_view_refuses_like_the_route(db, tmp_path, recipes):
    run = finished_run(db, tmp_path / "data")
    with pytest.raises(LookupError):
        fits_view(db, recipes, "run_nope")
    with pytest.raises(ValueError, match="doesn't measure 'height'"):
        fits_view(db, recipes, run.id, "height")


def test_a_timelapse_of_a_finished_run(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    seen = []
    out = make_timelapse(db, settings, recipes, run.id, seconds=1.0, progress=seen.append)
    assert out == RunFiles(settings.data_dir, run.experiment_id, run.id).media_path("timelapse")
    probe = ffprobe(out)
    assert (probe.width, probe.height) == (1920, 1080) and abs(probe.duration - 1.0) < 0.1
    assert seen[0] == 0.0 and seen[-1] == 1.0


def test_a_running_run_is_refused(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", status=RunStatus.RUNNING)
    with pytest.raises(MediaRefused, match="still running"):
        make_timelapse(db, settings, recipes, run.id, seconds=1.0)


def test_a_run_without_frames_is_refused(db, tmp_path, settings, recipes):
    experiment = repos.create_experiment(db, "Nothing recorded", "colour-reaction", 1)
    run = repos.create_run(db, experiment.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    repos.set_run_status(db, run.id, RunStatus.STOPPED)
    with pytest.raises(MediaRefused, match="no frames"):
        make_timelapse(db, settings, recipes, run.id, seconds=1.0)


def test_a_run_without_readings_has_no_curve_panel(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", readings=False)
    records = load_records(db, settings, recipes, run.id)
    assert chart_note(records.fits) == "No readings of colour change to draw"
    image = Drawer(records, settings).run_frame(schedule([f.t for f in records.frames], 0.1)[0])
    assert image.size == (1920, 1080) and image.mode == "RGB"


def test_no_model_is_called(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    make_timelapse(db, settings, recipes, run.id, seconds=0.5)
    assert logged_functions(db) == []


def test_the_credit_and_licence_are_never_cut():
    """Published data shows its credit and licence on every frame (D-70); the Genze credit is the longest we have."""
    from argus.media.draw import PANEL_R, PANEL_X, SOURCE_FONT, SOURCE_LINES, X2, wrap

    credit = (
        "Published data: Genze N., Bharti R., Grieb M., Schultheiss S.J., Grimm D.G. (2020), Plant Methods 16:157; "
        "cropped and tiled by Argus · CC BY 4.0"
    )
    lines = wrap(credit, SOURCE_FONT(), (PANEL_R - PANEL_X) * X2, SOURCE_LINES)
    assert lines[-1].endswith("CC BY 4.0") and not any("…" in line for line in lines)


def test_a_reel_of_a_finished_run(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    out = make_reel(db, settings, recipes, run.id, fps=2)  # fewer frames to draw; the length is the same
    assert out == RunFiles(settings.data_dir, run.experiment_id, run.id).media_path("reel")
    probe = ffprobe(out)
    assert (probe.width, probe.height) == (1920, 1080) and 30 - 0.2 <= probe.duration <= 60 + 0.2
    assert logged_functions(db) == []


def test_a_reel_of_a_one_frame_run_is_still_thirty_seconds(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", frames=1)
    probe = ffprobe(make_reel(db, settings, recipes, run.id, fps=2))
    assert 30 - 0.2 <= probe.duration <= 60 + 0.2
