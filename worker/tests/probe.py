"""What ffprobe says about a video: the media tests check real files, not our own idea of them."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace


def ffprobe(path: Path) -> SimpleNamespace:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name,pix_fmt",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    return SimpleNamespace(
        width=stream["width"],
        height=stream["height"],
        codec=stream["codec_name"],
        pix_fmt=stream["pix_fmt"],
        duration=float(data["format"]["duration"]),
    )
