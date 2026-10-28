"""segment() against recorded SAM 3.1 streams (tests/fixtures/sam, made by probes/record_sam.py). No network."""

import asyncio
import base64
import json
import time
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest
from pydantic import SecretStr
from skimage import data

from argus.config import Settings
from argus.pipeline.analyzer import SamSegmenter
from argus.segment import Clip, SegmentError, segment
from argus.segment.sam import sam_client

FIXTURES = Path(__file__).parent / "fixtures" / "sam"
SETTINGS = Settings(model_api_key=SecretStr("test-key"))
COINS = cv2.cvtColor(data.coins(), cv2.COLOR_GRAY2BGR)  # 384 x 303, the image the fixture was recorded on


def recorded(name: str) -> list[dict]:
    """The recorded stream events as dicts; meta-sam-parser reads mappings and SDK objects alike."""
    lines = (FIXTURES / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


class FakeResponses:
    def __init__(self, events=None, error=None):
        self.events, self.error, self.kwargs = events or [], error, None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error

        async def stream():
            for event in self.events:
                yield event

        return stream()


class FakeClient:
    def __init__(self, events=None, error=None):
        self.responses = FakeResponses(events, error)


def sent_image(fake: FakeClient) -> np.ndarray:
    content = fake.responses.kwargs["input"][0]["content"]
    url = next(c["image_url"] for c in content if c["type"] == "input_image")
    raw = base64.b64decode(url.split(",", 1)[1])
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "crop A é.mp4"
    path.write_bytes(b"not decoded by the fake client")
    return path


@pytest.mark.anyio
async def test_image_mode_returns_every_coin_as_a_frame_sized_patch():
    fake = FakeClient(recorded("coins-image"))
    result = await segment(COINS, "coin", mode="image", settings=SETTINGS, client=fake)
    assert len(result.tracks) == 24 and all(len(t.frames) == 1 and t.concept == "coin" for t in result.tracks)
    for track in result.tracks:
        patch = track.frames[0].patch
        assert patch.left >= 0 and patch.top >= 0
        assert patch.left + patch.mask.shape[1] <= 384 and patch.top + patch.mask.shape[0] <= 303
        assert patch.area_px > 100 and 0.9 <= track.frames[0].confidence <= 1.0
    call = result.call
    assert (call.status, call.images, call.frames, call.cost_usd) == ("ok", 1, 0, 0.0025)
    assert fake.responses.kwargs["model"] == "sam-3.1" and fake.responses.kwargs["stream"] is True
    assert fake.responses.kwargs["metadata"] == {"mask_encoding": "one_bit", "include_confidence": "true"}
    assert sent_image(fake).shape[:2] == (303, 384)


@pytest.mark.anyio
async def test_roi_crops_the_request_and_shifts_patches_back():
    fake = FakeClient(recorded("coins-image"))
    result = await segment(COINS, "coin", mode="image", roi=(100, 50, 300, 250), settings=SETTINGS, client=fake)
    assert sent_image(fake).shape[:2] == (200, 200)
    assert all(t.frames[0].patch.left >= 100 and t.frames[0].patch.top >= 50 for t in result.tracks)


@pytest.mark.anyio
async def test_video_mode_keeps_object_ids_across_frames(clip):
    fake = FakeClient(recorded("pan-video"))
    gaps: list[float] = []

    async def ticker():  # parsing takes seconds of CPU: the worker's event loop must keep answering meanwhile
        last = time.perf_counter()
        while True:
            await asyncio.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now

    beat = asyncio.create_task(ticker())
    result = await segment(Clip(clip, 60, 240, 240), "coin", mode="video", settings=SETTINGS, client=fake)
    beat.cancel()
    assert gaps and max(gaps) < 0.5
    assert 1 <= len(result.tracks) <= 16 and all(t.key.startswith("obj") for t in result.tracks)
    indices = [f.index for t in result.tracks for f in t.frames]
    assert min(indices) >= 0 and max(indices) <= 59 and max(len(t.frames) for t in result.tracks) > 30
    assert all(len({f.index for f in t.frames}) == len(t.frames) for t in result.tracks)  # one patch per frame
    assert (result.call.frames, result.call.images, result.call.cost_usd) == (60, 0, pytest.approx(0.012))
    assert fake.responses.kwargs["metadata"]["propagation_direction"] == "forward"


@pytest.mark.anyio
async def test_a_short_clip_is_billed_at_least_fifty_frames(clip):
    # A stream that arrived but was cut short is billed like a complete one, so it shows the billing quickly.
    events = recorded("pan-video")[:3]
    with pytest.raises(SegmentError) as caught:
        await segment(Clip(clip, 20, 240, 240), "coin", mode="video", settings=SETTINGS, client=FakeClient(events))
    assert caught.value.call.frames == 50 and caught.value.call.cost_usd == pytest.approx(0.01)


@pytest.mark.anyio
@pytest.mark.parametrize("concept", ["seed, root", "seed + root", ""])
async def test_one_concept_per_request(concept):
    with pytest.raises(ValueError):
        await segment(COINS, concept, mode="image", settings=SETTINGS, client=FakeClient())


@pytest.mark.anyio
async def test_a_clip_over_the_frame_limit_is_refused_before_any_request(clip):
    fake = FakeClient(recorded("pan-video"))
    with pytest.raises(ValueError, match="15000"):
        await segment(Clip(clip, 15001, 240, 240), "coin", mode="video", settings=SETTINGS, client=fake)
    assert fake.responses.kwargs is None


@pytest.mark.anyio
async def test_a_failed_stream_raises_with_a_logged_call():
    fake = FakeClient(error=httpx.ReadTimeout("timed out"))
    with pytest.raises(SegmentError) as caught:
        await segment(COINS, "coin", mode="image", settings=SETTINGS, client=fake)
    call = caught.value.call
    assert call.status == "error" and "ReadTimeout" in call.error and call.cost_usd == 0.0 and call.latency_s >= 0


@pytest.mark.anyio
async def test_a_stream_cut_short_is_a_failure():
    events = recorded("coins-image")[:-1]  # no response.completed
    with pytest.raises(SegmentError) as caught:
        await segment(COINS, "coin", mode="image", settings=SETTINGS, client=FakeClient(events))
    assert caught.value.call.status == "error"


@pytest.mark.anyio
async def test_one_attempt_is_one_http_request_with_a_bounded_wait():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(500, json={"error": {"message": "boom"}})

    client = sam_client(SETTINGS, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert client.timeout.read == SETTINGS.sam_timeout_s == 120.0 and client.timeout.connect == 5.0
    with pytest.raises(SegmentError):
        await segment(COINS, "coin", mode="image", settings=SETTINGS, client=client)
    assert len(requests) == 1  # no hidden SDK retries: the pipeline's attempts are the only ones, each logged


@pytest.mark.anyio
async def test_the_segmenter_keeps_one_client_and_closes_it():
    segmenter = SamSegmenter(SETTINGS)
    client = segmenter.client
    assert segmenter.client is client and client.max_retries == 0
    await segmenter.aclose()
    assert client.is_closed()
