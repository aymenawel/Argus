"""Videos over the API (spec §10): make one in the background, read its state, download the file."""

import threading

import pytest

from argus.domain import RunStatus
from argus.media import MediaError
from argus.storage import repos
from argus.storage.files import RunFiles
from tests.api_client import api_client, wait_for
from tests.records import finished_run


class Makers:
    """Fake video makers: each waits until released, reports progress, then writes a small file (or fails)."""

    def __init__(self, fail: str | None = None) -> None:
        self.release = threading.Event()
        self.fail = fail

    def maker(self, kind: str):
        def make(db, settings, recipes, run_id, *, progress):
            progress(0.5)
            self.release.wait(10)
            if self.fail:
                raise MediaError(self.fail)
            run = repos.get_run(db, run_id)
            path = RunFiles(settings.data_dir, run.experiment_id, run.id).media_path(kind)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x00" * 2048)
            return path

        return make

    def all(self) -> dict:
        return {"timelapse": self.maker("timelapse"), "reel": self.maker("reel")}


def states(client, run):
    return client.get(f"/api/runs/{run.id}/media").json()


def test_making_a_video_answers_202_then_becomes_ready(db, tmp_path):
    run = finished_run(db, tmp_path / "data")
    makers = Makers()
    with api_client(db, tmp_path, media_makers=makers.all()) as client:
        assert states(client, run) == {"timelapse": {"state": "none"}, "reel": {"state": "none"}}
        response = client.post(f"/api/runs/{run.id}/media/timelapse")
        assert response.status_code == 202 and response.json()["state"] == "running"
        assert wait_for(lambda: states(client, run)["timelapse"] == {"state": "running", "progress": 0.5})
        makers.release.set()
        state = wait_for(lambda: (s := states(client, run)["timelapse"])["state"] == "ready" and s)
        assert state["size_bytes"] == 2048 and state["made_at"]
        video = client.get(f"/api/runs/{run.id}/media/timelapse.mp4")
        assert video.status_code == 200 and video.headers["content-type"] == "video/mp4" and len(video.content) == 2048


def test_a_second_request_while_making_is_409(db, tmp_path):
    run = finished_run(db, tmp_path / "data")
    makers = Makers()
    with api_client(db, tmp_path, media_makers=makers.all()) as client:
        assert client.post(f"/api/runs/{run.id}/media/timelapse").status_code == 202
        again = client.post(f"/api/runs/{run.id}/media/timelapse")
        assert again.status_code == 409 and again.json()["detail"] == "a timelapse is already being made"
        assert client.post(f"/api/runs/{run.id}/media/reel").status_code == 202  # the other kind may run alongside
        makers.release.set()
        wait_for(lambda: all(s["state"] == "ready" for s in states(client, run).values()))


def test_a_running_run_is_refused_with_409(db, tmp_path):
    run = finished_run(db, tmp_path / "data")
    with api_client(db, tmp_path, media_makers=Makers().all()) as client:
        repos.set_run_status(db, run.id, RunStatus.RUNNING)  # after start-up, which stops runs left running
        refused = client.post(f"/api/runs/{run.id}/media/reel")
        assert refused.status_code == 409 and "still running" in refused.json()["detail"]


def test_a_failed_job_says_why(db, tmp_path):
    run = finished_run(db, tmp_path / "data")
    makers = Makers(fail="ffmpeg is not on PATH")
    makers.release.set()
    with api_client(db, tmp_path, media_makers=makers.all()) as client:
        client.post(f"/api/runs/{run.id}/media/timelapse")
        assert wait_for(lambda: states(client, run)["timelapse"]["state"] == "failed")
        assert states(client, run)["timelapse"] == {"state": "failed", "reason": "ffmpeg is not on PATH"}


def test_no_video_yet_is_404(db, tmp_path):
    run = finished_run(db, tmp_path / "data")
    with api_client(db, tmp_path, media_makers=Makers().all()) as client:
        missing = client.get(f"/api/runs/{run.id}/media/reel.mp4")
        assert missing.status_code == 404 and missing.json()["detail"] == "no reel yet"
        assert client.get("/api/runs/run_nope/media").status_code == 404


@pytest.mark.parametrize("method, path", [("post", "/media/poster"), ("get", "/media/poster.mp4")])
def test_an_unknown_kind_is_422(db, tmp_path, method, path):
    run = finished_run(db, tmp_path / "data")
    with api_client(db, tmp_path, media_makers=Makers().all()) as client:
        assert getattr(client, method)(f"/api/runs/{run.id}{path}").status_code == 422
