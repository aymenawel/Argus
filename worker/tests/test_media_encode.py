"""Encoding (D-84): frames go to the ffmpeg CLI as raw RGB; a failure leaves nothing half-written."""

import shutil

import pytest
from PIL import Image

from argus.media import MediaError
from argus.media.encode import encode
from tests.probe import ffprobe


def test_encode_makes_an_mp4_of_the_expected_duration(tmp_path):
    frames = (Image.new("RGB", (320, 180), c) for c in ("red", "green", "blue"))
    out = encode(frames, tmp_path / "x.mp4", fps=1, size=(320, 180))
    probe = ffprobe(out)
    assert (probe.width, probe.height, probe.codec, probe.pix_fmt) == (320, 180, "h264", "yuv420p")
    assert abs(probe.duration - 3.0) < 0.1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["x.mp4"]


def test_a_failed_encode_leaves_no_file(tmp_path):
    def frames():
        yield Image.new("RGB", (320, 180))
        raise RuntimeError("drawing failed")

    with pytest.raises(MediaError, match="drawing failed"):
        encode(frames(), tmp_path / "x.mp4", size=(320, 180))
    assert list(tmp_path.iterdir()) == []


def test_a_frame_of_the_wrong_size_is_refused(tmp_path):
    with pytest.raises(MediaError, match="320x180"):
        encode(iter([Image.new("RGB", (100, 100))]), tmp_path / "x.mp4", size=(320, 180))
    assert list(tmp_path.iterdir()) == []


def test_a_missing_ffmpeg_is_a_media_error(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(MediaError, match="ffmpeg is not on PATH"):
        encode(iter([]), tmp_path / "x.mp4")
