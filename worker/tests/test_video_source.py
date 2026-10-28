from pathlib import Path

import cv2
import numpy as np
import pytest

from argus.capture.video import VideoFileSource


def write_clip(path: Path, *, frames: int, fps: float, size=(96, 64)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for i in range(frames):
        image = np.full((size[1], size[0], 3), 255, np.uint8)
        cv2.rectangle(image, (0, 0), (i % size[0], 10), (0, 0, 0), -1)  # a bar that grows: frames differ
        writer.write(image)
    writer.release()
    return path


def test_split_files_with_different_frame_rates_give_continuous_time(tmp_path):
    a = write_clip(tmp_path / "dossier é" / "part 1 é.mp4", frames=20, fps=10)  # 0.0 .. 1.9 s
    b = write_clip(tmp_path / "part 2.mp4", frames=10, fps=5)  # continues at 2.0 s, step 0.2 s
    frames = list(VideoFileSource([a, b], time_scale=600).frames())
    ts = [f.t for f in frames]
    assert len(ts) == 30 and all(t2 > t1 for t1, t2 in zip(ts, ts[1:], strict=False))
    assert ts[19] == pytest.approx(1.9 * 600, rel=0.02) and ts[20] == pytest.approx(2.0 * 600, rel=0.02)
    assert ts[-1] == pytest.approx(3.8 * 600, rel=0.02)
    assert [f.file_index for f in frames] == [0] * 20 + [1] * 10
    assert frames[0].image.shape == (64, 96, 3) and frames[20].video_s == pytest.approx(2.0, rel=0.02)


def test_a_missing_file_is_named(tmp_path):
    with pytest.raises(FileNotFoundError, match="nope.mp4"):
        list(VideoFileSource([tmp_path / "nope.mp4"], time_scale=1).frames())


def test_a_file_that_is_not_a_video_is_named(tmp_path):
    bad = tmp_path / "notes.mp4"
    bad.write_text("not a video")
    with pytest.raises(FileNotFoundError, match="notes.mp4"):
        list(VideoFileSource([bad], time_scale=1).frames())
