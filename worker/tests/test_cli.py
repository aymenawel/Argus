import shutil

import pytest

from argus.cli import dev_commands


def test_dev_commands_start_worker_and_web(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: f"C:/bin/{name}.cmd")
    worker, web = dev_commands(tmp_path)
    assert worker.cwd == tmp_path / "worker"
    assert "argus.api.app:app_from_env" in worker.args
    assert worker.args[0].endswith("uv.cmd")
    assert web.cwd == tmp_path / "web"
    assert web.args[-2:] == ["run", "dev"]


def test_missing_tool_is_named(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "npm" else name)
    with pytest.raises(FileNotFoundError, match="npm"):
        dev_commands(tmp_path)
