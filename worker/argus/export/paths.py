"""Where a recorded answer lives in a bundle. web/lib/replay.ts names files by the same rule; both are checked
against tests/fixtures/bundle_paths.json."""

from __future__ import annotations

import re
from urllib.parse import unquote

SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe(part: str) -> bool:
    return bool(SAFE.match(part)) and part not in {".", ".."}


def bundle_file(path: str, query: str = "") -> str:
    """`/api/runs/r1/fits` with `metric=delta_e` → `api/runs/r1/fits__metric=delta_e.json`; query pairs sorted by key.
    Anything outside letters, digits, `_`, `.` and `-` is refused, so a name is the same on every file system."""
    segments = path.strip("/").split("/")
    if not all(_safe(s) for s in segments):
        raise ValueError(f"not a path a bundle can hold: {path!r}")
    name = "/".join(segments)
    if not query:
        return f"{name}.json"
    pairs = []
    for pair in query.split("&"):
        key, sep, value = pair.partition("=")
        value = unquote(value)
        if not sep or not _safe(key) or not _safe(value):
            raise ValueError(f"not a query a bundle can hold: {pair!r}")
        pairs.append((key, value))
    return f"{name}__" + "&".join(f"{k}={v}" for k, v in sorted(pairs)) + ".json"
