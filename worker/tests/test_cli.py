import os
import shutil

import pytest

from argus.cli import dev_commands, source_snapshot


def test_dev_commands_start_worker_and_web(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: f"C:/bin/{name}.cmd")
    worker, web = dev_commands(tmp_path)
    assert worker.cwd == tmp_path / "worker"
    assert "argus.api.app:app_from_env" in worker.args
    assert worker.args[0].endswith("uv.cmd")
    assert web.cwd == tmp_path / "web"
    assert web.args[-2:] == ["run", "dev"]


def test_the_runner_not_uvicorn_restarts_the_worker(monkeypatch, tmp_path):
    # On Windows uvicorn's --reload stops the server with a console Ctrl+C, which never arrives without a
    # console and hits every process (the runner, next dev) with one. An open page holds /api/events forever,
    # so shutdown is bounded too.
    monkeypatch.setattr(shutil, "which", lambda name: name)
    args = dev_commands(tmp_path)[0].args
    assert "--reload" not in args and args[args.index("--timeout-graceful-shutdown") + 1] == "1"


def test_source_snapshot_sees_worker_code_and_recipes_only(tmp_path):
    files = ["worker/argus/a.py", "worker/argus/storage/migrations/001_x.sql", "recipes/r.toml"]
    ignored = ["worker/argus/__pycache__/a.cpython-312.pyc", "web/app/page.tsx", "worker/tests/test_a.py"]
    for name in files + ignored:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x")
    before = source_snapshot(tmp_path)
    for name in ignored:
        os.utime(tmp_path / name, ns=(1, 1))
    assert source_snapshot(tmp_path) == before
    for name in files:
        os.utime(tmp_path / name, ns=(1, 1))
        assert source_snapshot(tmp_path) != before
        before = source_snapshot(tmp_path)
    (tmp_path / "worker/argus/new.py").write_text("x")
    assert source_snapshot(tmp_path) != before


def test_missing_tool_is_named(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "npm" else name)
    with pytest.raises(FileNotFoundError, match="npm"):
        dev_commands(tmp_path)
