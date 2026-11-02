"""Export a finished run as a bundle for the public replay (D-83).

The worker's own app answers the GET requests the Run and Results screens make, in-process, and each answer is saved
where web/lib/replay.ts will look for it, so the replay's shapes are the live API's by construction. The app is never
entered as a context manager: its lifespan marks runs still `running` as stopped, which an export must not do to a
run that is live right now. No model is called (no reasoner; a segmenter that refuses), nothing outside the output
folder is written, and a bundle is built in a temporary folder and only renamed into place once complete.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any

import cv2
import numpy as np
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.api.events import EventBroker
from argus.config import Settings
from argus.domain import EventKind, Run, RunMode, RunStatus
from argus.export.paths import bundle_file
from argus.export.thinning import Thinning, thin_frames
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database
from argus.storage.files import RunFiles

MB = 1_000_000
LONG_SIDE_PX = 1280
JPEG_QUALITY = 82
RUN_ID = re.compile(r"^[A-Za-z0-9_-]+$")
UNCITED = {EventKind.TICK, EventKind.CHECKIN}  # routine wake-ups, not moments anyone points at
MEDIA = ("timelapse", "reel")


class BundleRefused(Exception):
    """Why a run can't be bundled; the message is the reason."""


class NoModels:
    """A segmenter that refuses every call: the exporter records answers, it never asks a model."""

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def refuse(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("the bundle exporter never calls a model")

        return refuse


def public_run_view(view: dict) -> dict:
    """A run's view as the public replay shows it: its source files by name only, never this laptop's folders (the
    user's own name is often one of them). The UI never reads them; the names say what was imported."""
    source = view["run"]["source"]
    public = {
        **source,
        "paths": [PureWindowsPath(p).name for p in source.get("paths") or []],
        "manifest": PureWindowsPath(source["manifest"]).name if source.get("manifest") else None,
    }
    return {**view, "run": {**view["run"], "source": public}}


def source_label(run: Run) -> str:
    if run.source.provenance is not None:
        return "published data"
    return "live recording" if run.mode is RunMode.LIVE else "imported recording"


def _recorder(db: Database, settings: Settings, recipes: Mapping[str, Recipe]) -> TestClient:
    broker, hub = EventBroker(), CameraHub()
    jobs = RunJobs(db, broker, settings, recipes, hub, segmenter=NoModels(), reasoner=None)
    # Not `with TestClient(...)`: entering it would run the lifespan (see the module docstring).
    return TestClient(create_app(settings, db, broker, dict(recipes), jobs=jobs, hub=hub))


class _Writer:
    def __init__(self, client: TestClient, folder: Path) -> None:
        self.client, self.folder = client, folder

    def record(self, path: str, query: str = "", keep: Callable[[Any], Any] | None = None) -> Any:
        """GET path, save the answer at its bundle name and return it. A refusal is saved as a recorded error."""
        response = self.client.get(f"{path}?{query}" if query else path)
        if response.status_code == 200:
            body = response.json()
            body = keep(body) if keep is not None else body
        else:
            detail = response.json().get("detail") if response.content else None
            body = {"argus_recorded_error": response.status_code, "detail": detail}
        file = self.folder / bundle_file(path, query)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        return body


def _cited_t(timeline: dict, notes: Any, verdict: Any) -> list[float]:
    """Times someone points at: each note, each event that isn't a routine wake-up (and its frames), the verdict."""
    frame_t = {f["id"]: f["t"] for f in timeline["frames"]}
    cited = [n["t"] for n in notes.get("notes", [])] if isinstance(notes, dict) else []
    for event in timeline["events"]:
        if event["kind"] in UNCITED:
            continue
        cited.append(event["t_start"])
        cited += [frame_t[i] for i in event.get("frame_ids", []) if i in frame_t]
    if isinstance(verdict, dict) and "t" in verdict:
        cited.append(verdict["t"])
    return cited


def _write_frame(source: Path, out: Path) -> float:
    """Write the frame at most LONG_SIDE_PX on its long side; returns how much it shrank (original / written)."""
    image = cv2.imdecode(np.frombuffer(source.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise BundleRefused(f"a frame can't be read: {source}")
    height, width = image.shape[:2]
    scale = LONG_SIDE_PX / max(height, width)
    if scale < 1:  # never enlarged
        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise BundleRefused(f"a frame can't be encoded: {source}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(encoded.tobytes())
    return max(height, width) / max(image.shape[:2])


def _thinning_note(thinning: Thinning) -> str | None:
    total, shown = len(thinning.frame_map), len(thinning.kept)
    if shown == total:
        return None
    return f"1 picture in {round(total / shown)} shown; measurements use all {total:,} pictures"


def _build(
    folder: Path,
    db: Database,
    settings: Settings,
    recipes: Mapping[str, Recipe],
    run: Run,
    commit: str | None,
    max_frames: int,
) -> dict:
    writer = _Writer(_recorder(db, settings, recipes), folder)
    experiment_path, run_path = f"/api/experiments/{run.experiment_id}", f"/api/runs/{run.id}"
    writer.record(experiment_path)
    detail = writer.record(f"{experiment_path}/recipe/detail")
    writer.record(
        f"{experiment_path}/runs", keep=lambda runs: [public_run_view(r) for r in runs if r["run"]["id"] == run.id]
    )
    writer.record(f"{experiment_path}/plan")
    writer.record(run_path, keep=public_run_view)
    timeline = writer.record(f"{run_path}/timeline")
    notes = writer.record(f"{run_path}/notes")
    verdict = writer.record(f"{run_path}/verdict")
    writer.record(f"{run_path}/reviews")
    writer.record(f"{run_path}/fits")
    for metric in detail["metrics"]:
        writer.record(f"{run_path}/fits", f"metric={metric['id']}")
        writer.record(f"{run_path}/agreement", f"metric={metric['id']}")
    writer.record(f"{run_path}/next-run")
    writer.record(f"{run_path}/media")  # the Videos card: in the replay it offers the copies below for download

    thinning = thin_frames(
        [(f["id"], f["t"]) for f in timeline["frames"]], _cited_t(timeline, notes, verdict), max_frames
    )
    paths = {f.id: f.path for f in repos.frames_for_run(db, run.id)}
    scales = []
    for frame_id in thinning.kept:
        writer.record(f"{run_path}/frames/{frame_id}/detections")
        scales.append(_write_frame(settings.data_dir / paths[frame_id], folder / "frames" / f"{frame_id}.jpg"))

    files = RunFiles(settings.data_dir, run.experiment_id, run.id)
    media = []
    for kind in MEDIA:
        source = files.media_path(kind)
        if source.is_file():
            shutil.copyfile(source, folder / f"{kind}.mp4")
            media.append(f"{kind}.mp4")

    experiment = repos.get_experiment(db, run.experiment_id)
    provenance = run.source.provenance
    manifest = {
        "run_id": run.id,
        "experiment_id": run.experiment_id,
        "experiment_title": experiment.title if experiment else "",
        "source_label": source_label(run),
        "credit": provenance.credit if provenance else None,
        "licence": provenance.licence if provenance else None,
        "dataset_url": provenance.url if provenance else None,
        # When the footage was filmed, if known (an import's start time), not when Argus ran: the replay dates it.
        "recorded": (run.source.start_time or run.started_at).isoformat(),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit,
        "frames": {
            "total": len(thinning.frame_map),
            "shown": len(thinning.kept),
            "note": _thinning_note(thinning),
            # Regions and outlines are in the original frames' pixels: the replay multiplies a shown frame's size by
            # this. One run's frames come from one source, so the first frame's factor holds for all of them.
            "scale": round(scales[0], 6) if scales else 1.0,
        },
        "frame_map": thinning.frame_map,
        "media": media,
        "verdict": verdict.get("verdict") if isinstance(verdict, dict) else None,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def _update_index(out_dir: Path, manifest: dict) -> None:
    path = out_dir / "index.json"
    runs = json.loads(path.read_text(encoding="utf-8"))["runs"] if path.is_file() else []
    entry = {
        "run_id": manifest["run_id"],
        "experiment_id": manifest["experiment_id"],
        "title": manifest["experiment_title"],
        "source_label": manifest["source_label"],
        "recorded": manifest["recorded"],
        "verdict": manifest["verdict"],
    }
    runs = [r for r in runs if r["run_id"] != entry["run_id"]] + [entry]
    runs.sort(key=lambda r: r["recorded"], reverse=True)
    temp = out_dir / "index.json.tmp"
    temp.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    temp.replace(path)


def export_bundle(
    db: Database,
    settings: Settings,
    recipes: Mapping[str, Recipe],
    run_id: str,
    out_dir: Path,
    *,
    commit: str | None = None,
    max_frames: int = 400,
    max_bytes: int = 60 * MB,
) -> Path:
    """Write out_dir/<run_id>/ and list it in out_dir/index.json; re-exporting replaces both."""
    if not RUN_ID.match(run_id):
        raise BundleRefused(f"not a run id: {run_id!r}")
    run = repos.get_run(db, run_id)
    if run is None:
        raise BundleRefused(f"run not found: {run_id}")
    if run.status is RunStatus.RUNNING:
        raise BundleRefused("the run is still running: export it once it has finished or been stopped")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    temp = out_dir / f".{run_id}.tmp"
    shutil.rmtree(temp, ignore_errors=True)
    try:
        manifest = _build(temp, db, settings, recipes, run, commit, max_frames)
        size = sum(f.stat().st_size for f in temp.rglob("*") if f.is_file())
        if size > max_bytes:
            raise BundleRefused(f"the bundle is {size / MB:.1f} MB, over the {max_bytes / MB:g} MB limit")
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    final = out_dir / run_id
    shutil.rmtree(final, ignore_errors=True)
    temp.rename(final)
    _update_index(out_dir, manifest)
    return final
