"""Argus command line. From worker/:

uv run python -m argus dev              start the worker API and the web app together
uv run python -m argus card --out PATH  export the printable Argus Card sheet
"""

from __future__ import annotations

import argparse
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
    uv, npm = _tool("uv"), _tool("npm")
    worker = [uv, "run", "--env-file", "../.env", "uvicorn", "--factory", "argus.api.app:app_from_env"]
    return [
        Command([*worker, "--reload", "--port", "8000"], repo / "worker"),
        Command([npm, "run", "dev"], repo / "web"),
    ]


def _stop(proc: subprocess.Popen[bytes]) -> None:
    """Stop a process and everything it started (uvicorn's reloader, next dev's node)."""
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


def run_dev(repo: Path) -> int:
    env_file = repo / ".env"
    if not env_file.is_file():
        print(f"No {env_file}. Copy .env.example to .env first (the API key may stay empty).", file=sys.stderr)
        return 1
    commands = dev_commands(repo)
    procs = [subprocess.Popen(c.args, cwd=c.cwd, start_new_session=os.name != "nt") for c in commands]
    print("Argus: worker on http://localhost:8000, web app on http://localhost:3000. Ctrl+C stops both.", flush=True)
    try:
        while True:
            for command, proc in zip(commands, procs, strict=True):
                code = proc.poll()
                if code is not None:
                    print(f"{Path(command.args[0]).name} exited with {code}; stopping the other.", file=sys.stderr)
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in procs:
            _stop(proc)


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
