"""The run bundle (D-83): the worker's own answers to the Run and Results screens, recorded in-process, with thinned
frames and a manifest the public replay reads."""

import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from argus.config import REPO_ROOT, load_settings
from argus.domain import RunStatus
from argus.export.bundle import BundleRefused, export_bundle, public_run_view
from argus.export.paths import bundle_file
from argus.export.thinning import thin_frames
from argus.recipes.loader import load_all
from argus.storage import repos
from argus.storage.files import RunFiles
from tests.api_client import api_client, logged_functions
from tests.records import PROVENANCE, finished_run

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings(tmp_path):
    return load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data")})


@pytest.fixture
def recipes():
    return load_all(REPO_ROOT / "recipes")


def export(db, settings, recipes, run, tmp_path, **kwargs) -> Path:
    return export_bundle(db, settings, recipes, run.id, tmp_path / "bundles", **kwargs)


def test_bundle_file_names_match_the_shared_fixture():
    for case in json.loads((FIXTURES / "bundle_paths.json").read_text(encoding="utf-8")):
        assert bundle_file(case["path"], case["query"]) == case["file"]


def test_a_query_value_outside_the_safe_set_is_refused():
    with pytest.raises(ValueError):
        bundle_file("/api/runs/r/fits", "metric=a/b")


def test_thinning_keeps_every_frame_under_the_limit():
    frames = [(f"f{i}", i * 10.0) for i in range(400)]
    thinning = thin_frames(frames, [], limit=400)
    assert thinning.kept == [f for f, _ in frames] and thinning.frame_map["f7"] == "f7"


def test_thinning_keeps_even_steps_and_cited_frames():
    frames = [(f"f{i}", i * 10.0) for i in range(1000)]
    thinning = thin_frames(frames, cited_t=[5551.0], limit=400)
    assert 400 <= len(thinning.kept) <= 401 and "f555" in thinning.kept
    assert set(thinning.frame_map) == {f for f, _ in frames} and set(thinning.frame_map.values()) <= set(thinning.kept)


def test_irregular_t_maps_to_the_nearest_kept_frame():
    frames = [("a", 0.0), ("b", 1.0), ("c", 2.0), ("d", 50.0), ("e", 51.0)]
    thinning = thin_frames(frames, [], limit=2)  # keeps a and e
    assert thinning.frame_map == {"a": "a", "b": "a", "c": "a", "d": "e", "e": "e"}


def recorded_requests(bundle: Path) -> list[tuple[str, dict[str, str], Path]]:
    found = []
    for file in sorted((bundle / "api").rglob("*.json")):
        name = file.relative_to(bundle).as_posix().removesuffix(".json")
        path, _, query = name.partition("__")
        params = dict(pair.split("=", 1) for pair in query.split("&")) if query else {}
        found.append(("/" + path, params, file))
    return found


def test_each_recorded_response_equals_the_live_response(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    bundle = export(db, settings, recipes, run, tmp_path)
    requests = recorded_requests(bundle)
    paths = {path for path, _, _ in requests}
    assert f"/api/runs/{run.id}/timeline" in paths and f"/api/experiments/{run.experiment_id}/plan" in paths
    assert {p["metric"] for path, p, _ in requests if path.endswith("/fits") and p} == {"delta_e"}
    with api_client(db, tmp_path) as client:
        for path, params, file in requests:
            live = client.get(path, params=params)
            body = live.json()
            if path == f"/api/experiments/{run.experiment_id}/runs":
                body = [public_run_view(r) for r in body if r["run"]["id"] == run.id]
            elif path == f"/api/runs/{run.id}":
                body = public_run_view(body)
            recorded = json.loads(file.read_text(encoding="utf-8"))
            if live.status_code == 200:
                assert recorded == body, path
            else:
                assert recorded == {"argus_recorded_error": live.status_code, "detail": body["detail"]}, path


def test_frames_are_shrunk_never_enlarged(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", frames=3)
    big = repos.frames_for_run(db, run.id)[0]
    cv2.imwrite(str(settings.data_dir / big.path), np.full((1200, 1600, 3), 90, np.uint8))
    bundle = export(db, settings, recipes, run, tmp_path)
    sizes = {
        f.id: cv2.imread(str(bundle / "frames" / f"{f.id}.jpg")).shape[:2] for f in repos.frames_for_run(db, run.id)
    }
    assert sizes[big.id] == (960, 1280)
    # Outlines and regions are in the original frame's pixels: the replay scales the shown frame back by this.
    assert json.loads((bundle / "manifest.json").read_text("utf-8"))["frames"]["scale"] == 1.25
    assert all(shape == (480, 640) for frame_id, shape in sizes.items() if frame_id != big.id)


def test_a_running_run_is_refused(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", status=RunStatus.RUNNING)
    with pytest.raises(BundleRefused, match="still running"):
        export(db, settings, recipes, run, tmp_path)


def test_an_oversize_bundle_is_refused_and_leaves_nothing(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    with pytest.raises(BundleRefused, match=r"MB, over the"):
        export(db, settings, recipes, run, tmp_path, max_bytes=1000)
    out = tmp_path / "bundles"
    assert not out.exists() or [p.name for p in out.iterdir()] in ([], ["index.json"])
    if (out / "index.json").exists():
        assert json.loads((out / "index.json").read_text(encoding="utf-8"))["runs"] == []


def test_exporting_leaves_a_running_run_running(db, tmp_path, settings, recipes):
    live = finished_run(db, tmp_path / "data", status=RunStatus.RUNNING)
    run = finished_run(db, tmp_path / "data")
    export(db, settings, recipes, run, tmp_path)
    assert repos.get_run(db, live.id).status is RunStatus.RUNNING


def test_reexport_replaces_the_folder_and_its_index_entry(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    bundle = export(db, settings, recipes, run, tmp_path)
    (bundle / "stale.txt").write_text("old", encoding="utf-8")
    bundle = export(db, settings, recipes, run, tmp_path)
    assert not (bundle / "stale.txt").exists()
    index = json.loads((tmp_path / "bundles" / "index.json").read_text(encoding="utf-8"))
    assert [entry["run_id"] for entry in index["runs"]] == [run.id]
    assert set(index["runs"][0]) == {"run_id", "experiment_id", "title", "source_label", "recorded", "verdict"}


def test_no_model_is_called(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    export(db, settings, recipes, run, tmp_path)
    assert logged_functions(db) == []


def test_manifest_labels_published_data_with_its_credit(db, tmp_path, settings, recipes):
    published = finished_run(db, tmp_path / "data", provenance=PROVENANCE)
    manifest = json.loads((export(db, settings, recipes, published, tmp_path) / "manifest.json").read_text("utf-8"))
    assert set(manifest) == {
        "run_id",
        "experiment_id",
        "experiment_title",
        "source_label",
        "credit",
        "licence",
        "dataset_url",
        "recorded",
        "exported_at",
        "commit",
        "frames",
        "frame_map",
        "media",
        "verdict",
    }
    assert manifest["source_label"] == "published data"
    assert (manifest["credit"], manifest["licence"], manifest["dataset_url"]) == (
        PROVENANCE.credit,
        PROVENANCE.licence,
        PROVENANCE.url,
    )
    assert manifest["frames"] == {"total": 12, "shown": 12, "note": None, "scale": 1.0} and manifest["media"] == []
    imported = finished_run(db, tmp_path / "data")
    manifest = json.loads((export(db, settings, recipes, imported, tmp_path) / "manifest.json").read_text("utf-8"))
    assert manifest["source_label"] == "imported recording" and manifest["credit"] is None


def test_a_thinned_manifest_says_so(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data", frames=1000, t_step=10.0, size=(32, 24))
    manifest = json.loads(
        (export(db, settings, recipes, run, tmp_path, max_frames=200) / "manifest.json").read_text("utf-8")
    )
    shown = manifest["frames"]["shown"]
    assert 200 <= shown <= 205 and len(list((tmp_path / "bundles" / run.id / "frames").iterdir())) == shown
    assert manifest["frames"] == {
        "total": 1000,
        "shown": shown,
        "note": f"1 picture in {round(1000 / shown)} shown; measurements use all 1,000 pictures",
        "scale": 1.0,
    }
    assert len(manifest["frame_map"]) == 1000


def test_media_states_are_recorded_and_made_videos_copied(db, tmp_path, settings, recipes):
    run = finished_run(db, tmp_path / "data")
    made = RunFiles(settings.data_dir, run.experiment_id, run.id).media_path("timelapse")
    made.parent.mkdir(parents=True)
    made.write_bytes(b"\x00" * 4096)
    bundle = export(db, settings, recipes, run, tmp_path)
    assert (bundle / "timelapse.mp4").read_bytes() == made.read_bytes() and not (bundle / "reel.mp4").exists()
    assert json.loads((bundle / "manifest.json").read_text("utf-8"))["media"] == ["timelapse.mp4"]
    recorded = json.loads((bundle / "api" / "runs" / run.id / "media.json").read_text("utf-8"))
    assert recorded["timelapse"]["state"] == "ready" and recorded["reel"] == {"state": "none"}


def test_local_paths_never_reach_the_public_bundle(db, tmp_path, settings, recipes):
    """A run's source names files on this laptop, under the user's own folder: the replay keeps only their names."""
    clip = r"C:\Users\someone\Videos\dye run.mp4"
    run = finished_run(db, tmp_path / "data", paths=[clip, "/home/someone/clips/b.mp4"])
    bundle = export(db, settings, recipes, run, tmp_path)
    for file in (bundle / "api").rglob("*.json"):
        text = file.read_text(encoding="utf-8")
        assert "someone" not in text, file
    view = json.loads((bundle / "api" / "runs" / f"{run.id}.json").read_text("utf-8"))
    assert view["run"]["source"]["paths"] == ["dye run.mp4", "b.mp4"]


def test_a_recording_is_dated_when_it_was_recorded_not_when_argus_imported_it(db, tmp_path, settings, recipes):
    """An imported recording with its start time given: the replay says when it was filmed, not when it was imported."""
    filmed = datetime(2026, 10, 29, 3, 22, 55, tzinfo=UTC)
    run = finished_run(db, tmp_path / "data", start_time=filmed)
    manifest = json.loads((export(db, settings, recipes, run, tmp_path) / "manifest.json").read_text("utf-8"))
    assert datetime.fromisoformat(manifest["recorded"]) == filmed
