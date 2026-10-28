"""Where a run's files live: data/<experiment>/<run>/{frames,masks,crops}/ (spec §5)."""

from __future__ import annotations

import re
from pathlib import Path


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-") or "x"


class RunFiles:
    def __init__(self, data_dir: Path, experiment_id: str, run_id: str) -> None:
        self.root = Path(data_dir) / experiment_id / run_id

    def _in(self, folder: str, name: str) -> Path:
        path = self.root / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def frame_path(self, frame_id: str) -> Path:
        return self._in("frames", f"{frame_id}.jpg")

    def mask_path(self, detection_id: str) -> Path:
        return self._in("masks", f"{detection_id}.png")

    def crop_path(self, label: str, concept: str) -> Path:
        return self._in("crops", f"{_slug(label)}-{_slug(concept.lower())}.mp4")
