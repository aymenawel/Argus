"""Argus command line. From worker/:

uv run python -m argus dev              start the worker API and the web app together
uv run python -m argus run FILE.json    start a run described in a JSON file (the worker must be running)
uv run python -m argus card --out PATH  export the printable Argus Card sheet
uv run python -m argus export-bundle RUN_ID   bundle a finished run for the public replay (web/public/bundles)
uv run python -m argus media timelapse RUN_ID make the run's timelapse (data/<experiment>/<run>/media/)
uv run python -m argus media reel RUN_ID      make the run's 30-60 s highlights reel
uv run python -m argus validation [--runs ID...]  print the README's validation table from the database
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from argus.config import REPO_ROOT


@dataclass(frozen=True)
class Command:
    args: list[str]
    cwd: Path


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"{name} is not on PATH; install it to run the dev servers")
    return path


def dev_commands(repo: Path) -> list[Command]:
    """The worker and the web app. The worker has no --reload: the runner restarts it (see run_dev)."""
    uv, npm = _tool("uv"), _tool("npm")
    worker = [uv, "run", "--env-file", "../.env", "uvicorn", "--factory", "argus.api.app:app_from_env"]
    # An open page holds /api/events forever, so stopping must not wait for streams to end on their own.
    return [
        Command([*worker, "--timeout-graceful-shutdown", "1", "--port", "8000"], repo / "worker"),
        Command([npm, "run", "dev"], repo / "web"),
    ]


# What the worker runs: a change to any of these restarts it.
WATCHED = (("worker/argus", "*.py"), ("worker/argus", "*.sql"), ("recipes", "*.toml"))


def source_snapshot(repo: Path) -> frozenset[tuple[str, int]]:
    """The worker's code, migrations and recipes with their modification times."""
    snapshot = set()
    for folder, pattern in WATCHED:
        for path in (repo / folder).rglob(pattern):
            with contextlib.suppress(FileNotFoundError):  # deleted while we looked: the next snapshot sees it
                snapshot.add((str(path), path.stat().st_mtime_ns))
    return frozenset(snapshot)


def _stop(proc: subprocess.Popen[bytes]) -> None:
    """Stop a process and everything it started (uv's uvicorn, next dev's node)."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _start(command: Command) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command.args, cwd=command.cwd, start_new_session=os.name != "nt")


def run_dev(repo: Path) -> int:
    """Run both until Ctrl+C. The worker restarts when its code changes (and comes back after a crash once
    the code is saved again); if the web app exits, everything stops.

    The runner restarts the worker itself, by stopping its process tree, because uvicorn's --reload stops the
    server with a console Ctrl+C on Windows: without a console it never arrives, and in a console it also
    reaches this runner and next dev.
    """
    env_file = repo / ".env"
    if not env_file.is_file():
        print(f"No {env_file}. Copy .env.example to .env first (the API key may stay empty).", file=sys.stderr)
        return 1
    worker_command, web_command = dev_commands(repo)
    worker, web = _start(worker_command), _start(web_command)
    sources, worker_down = source_snapshot(repo), False
    print("Argus: worker on http://localhost:8000, web app on http://localhost:3000. Ctrl+C stops both.", flush=True)
    try:
        while True:
            time.sleep(0.5)
            if (code := web.poll()) is not None:
                print(f"The web app exited with {code}; stopping the worker.", file=sys.stderr, flush=True)
                return code or 1
            if not worker_down and (code := worker.poll()) is not None:
                worker_down = True
                print(f"The worker exited with {code}. Save a change to restart it.", file=sys.stderr, flush=True)
            current = source_snapshot(repo)
            if current != sources:
                sources = current
                print("Worker code changed: restarting the worker.", flush=True)
                _stop(worker)
                worker, worker_down = _start(worker_command), False
    except KeyboardInterrupt:
        return 0
    finally:
        _stop(worker)
        _stop(web)


def post_run(path: Path, api: str) -> int:
    """POST the file's run to the worker. The file holds RunCreate fields plus `experiment_id`."""
    body = json.loads(path.read_text(encoding="utf-8"))
    experiment_id = body.pop("experiment_id")
    response = requests.post(f"{api.rstrip('/')}/api/experiments/{experiment_id}/runs", json=body, timeout=30)
    if response.status_code != 201:
        print(f"The worker refused the run ({response.status_code}): {response.text}", file=sys.stderr)
        return 1
    run_id = response.json()["run"]["id"]
    print(f"Run {run_id} started. Watch it at http://localhost:3000/experiments/{experiment_id}/run")
    return 0


def git_commit(repo: Path) -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def export_bundle_command(run_id: str, out: Path, max_frames: int) -> int:
    from argus.config import load_settings
    from argus.export.bundle import BundleRefused, export_bundle
    from argus.recipes.loader import load_all
    from argus.storage.db import Database

    settings = load_settings()
    db = Database(settings.data_dir / "argus.sqlite")
    try:
        folder = export_bundle(
            db,
            settings,
            load_all(settings.recipes_dir),
            run_id,
            out,
            commit=git_commit(REPO_ROOT),
            max_frames=max_frames,
        )
    except BundleRefused as refused:
        print(f"Not bundled: {refused}", file=sys.stderr)
        return 1
    finally:
        db.close()
    size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    print(f"{folder}  ({size / 1_000_000:.1f} MB, {manifest['frames']['shown']} frames)")
    if manifest["frames"]["note"]:
        print(manifest["frames"]["note"])
    return 0


def media_command(kind: str, run_id: str, seconds: float) -> int:
    from argus.config import load_settings
    from argus.media import MediaError, MediaRefused
    from argus.media.make import make_reel, make_timelapse
    from argus.recipes.loader import load_all
    from argus.storage.db import Database

    settings = load_settings()
    db = Database(settings.data_dir / "argus.sqlite")
    started = time.monotonic()
    try:
        recipes = load_all(settings.recipes_dir)
        if kind == "reel":
            out = make_reel(db, settings, recipes, run_id)
        else:
            out = make_timelapse(db, settings, recipes, run_id, seconds=seconds)
    except (MediaRefused, MediaError) as error:
        print(f"No {kind}: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"{out}  ({out.stat().st_size / 1_000_000:.1f} MB, made in {time.monotonic() - started:.0f} s)")
    return 0


def validation_command(run_ids: list[str] | None) -> int:
    from argus.analyze.validation import render_table, validation_rows
    from argus.config import load_settings
    from argus.recipes.loader import load_all
    from argus.storage.db import Database

    settings = load_settings()
    db = Database(settings.data_dir / "argus.sqlite")
    try:
        table = render_table(validation_rows(db, load_all(settings.recipes_dir), run_ids))
    finally:
        db.close()
    sys.stdout.reconfigure(encoding="utf-8")  # ±, × and → survive a Windows pipe into the README
    print(table)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus", description="Argus command line")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dev", help="start the worker API and the web app together")
    run = sub.add_parser("run", help="start a run described in a JSON file (the worker must be running)")
    run.add_argument("file", type=Path, help="RunCreate fields plus experiment_id, as JSON")
    run.add_argument("--api", default="http://localhost:8000", help="the worker's address")
    card = sub.add_parser("card", help="export the printable Argus Card sheet (SVG, PDF, PNG preview)")
    card.add_argument("--out", type=Path, required=True, help="folder to write the files into")
    dataset = sub.add_parser("dataset", help="turn a published dataset into a plate Argus can import")
    dataset.add_argument("name", choices=["genze"], help="the dataset")
    dataset.add_argument("--zip", type=Path, required=True, help="the dataset's archive, as downloaded")
    dataset.add_argument("--out", type=Path, required=True, help="folder for the plate's frames and manifest.json")
    bundle = sub.add_parser("export-bundle", help="bundle a finished run for the public replay (D-83)")
    bundle.add_argument("run_id", help="the run to bundle; it must have finished or been stopped")
    bundle.add_argument("--out", type=Path, default=REPO_ROOT / "web" / "public" / "bundles", help="bundles folder")
    bundle.add_argument("--max-frames", type=int, default=400, help="thin to about this many frames (default 400)")
    media = sub.add_parser("media", help="make a finished run's timelapse or highlights reel (D-84, D-85)")
    media.add_argument("kind", choices=["timelapse", "reel"], help="which video")
    media.add_argument("run_id", help="the run; it must have finished or been stopped")
    media.add_argument("--seconds", type=float, default=20.0, help="length of the timelapse (default 20)")
    validation = sub.add_parser("validation", help="print the validation table from the database (D-86)")
    validation.add_argument("--runs", nargs="+", metavar="RUN_ID", help="these runs (default: every finished one)")
    args = parser.parse_args(argv)

    if args.command == "dev":
        return run_dev(REPO_ROOT)
    if args.command == "run":
        return post_run(args.file, args.api)
    if args.command == "validation":
        return validation_command(args.runs)
    if args.command == "media":
        return media_command(args.kind, args.run_id, args.seconds)
    if args.command == "export-bundle":
        return export_bundle_command(args.run_id, args.out, args.max_frames)
    if args.command == "dataset":
        from argus.datasets import genze

        manifest = genze.build_plate(args.zip, args.out, dishes=genze.DEFAULT_PLATE, expected_sha256=genze.GENZE_SHA256)
        print(f"{len(manifest.tiles)} dishes, {len(manifest.frames)} frames: {args.out / 'manifest.json'}")
        return 0
    from argus.calibration import card_export  # needs a Chromium browser, so only loaded on demand

    for path in card_export.export(args.out):
        print(path)
    return 0
