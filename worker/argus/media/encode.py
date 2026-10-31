"""Frames to an MP4 with the ffmpeg CLI (D-45, D-84): raw RGB on stdin, H.264, yuv420p, `+faststart` so a browser
starts playing before the download ends. Written to a .part name and renamed only once ffmpeg has finished."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from argus.media import MediaError


def _last_line(stream) -> str:
    stream.seek(0)
    lines = [line.strip() for line in stream.read().decode("utf-8", "replace").splitlines() if line.strip()]
    return lines[-1] if lines else "no message"


def encode(
    frames: Iterable[Image.Image],
    out: Path,
    *,
    fps: int = 30,
    size: tuple[int, int] = (1920, 1080),
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MediaError("ffmpeg is not on PATH")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(f"{out.stem}.part{out.suffix}")
    width, height = size
    command = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
        str(part),
    ]  # fmt: skip
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
        assert process.stdin is not None
        try:
            for frame in frames:
                if frame.size != size:
                    raise MediaError(f"a {frame.size[0]}x{frame.size[1]} frame in a {width}x{height} video")
                process.stdin.write(frame.convert("RGB").tobytes())
            process.stdin.close()
            code = process.wait()
        except BrokenPipeError:
            code = process.wait()  # ffmpeg stopped reading: its own message says why
        except BaseException as error:
            process.kill()
            process.wait()
            part.unlink(missing_ok=True)
            if isinstance(error, MediaError) or not isinstance(error, Exception):
                raise
            raise MediaError(str(error) or type(error).__name__) from error
        if code != 0:
            part.unlink(missing_ok=True)
            raise MediaError(f"ffmpeg failed: {_last_line(errors)}")
    part.replace(out)
    return out
