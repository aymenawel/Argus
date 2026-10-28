"""Argus command line. From worker/:

uv run python -m argus dev              start the worker API and the web app together
uv run python -m argus card --out PATH  export the printable Argus Card sheet
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus", description="Argus command line")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dev", help="start the worker API and the web app together")
    card = sub.add_parser("card", help="export the printable Argus Card sheet (SVG, PDF, PNG preview)")
    card.add_argument("--out", type=Path, required=True, help="folder to write the files into")
    args = parser.parse_args(argv)

    if args.command == "dev":
        return run_dev(REPO_ROOT)
    from argus.calibration import card_export  # needs a Chromium browser, so only loaded on demand

    for path in card_export.export(args.out):
        print(path)
    return 0
