"""SAM 3.1 over Meta's Responses API: one concept per request, streamed, parsed with meta-sam-parser (KB 04).

This is the only module that talks to the segmentation model. Every request produces a ModelCallDraft with
its cost, success or failure, for the caller to log against the run.
"""

from __future__ import annotations

import asyncio
import base64
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

import cv2
import numpy as np
from meta_sam_parser import (
    CompletedOutcome,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    image_segmentation_format,
    parse_responses_stream,
    video_segmentation_format,
)
from openai import AsyncOpenAI, Timeout

from argus.config import Settings
from argus.domain import ModelCallDraft
from argus.segment.types import Clip, MaskPatch, Track, TrackFrame

METADATA = {"mask_encoding": "one_bit", "include_confidence": "true"}
JPEG_QUALITY = 90


class SegmentError(RuntimeError):
    """A failed segmentation, carrying the model call to log (status "error")."""

    def __init__(self, message: str, call: ModelCallDraft) -> None:
        super().__init__(message)
        self.call = call


def _check_concept(concept: str) -> None:
    if not concept.strip() or "," in concept or "+" in concept:
        raise ValueError(f"SAM takes exactly one concept per request, got {concept!r}")


def _jpeg_url(image_bgr: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise ValueError("JPEG encoding failed")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode()


def _mp4_url(clip: Clip) -> str:
    return "data:video/mp4;base64," + base64.b64encode(clip.path.read_bytes()).decode()


def _patch(record: SegmentationMaskRecord) -> MaskPatch:
    raw = np.frombuffer(decode_mask_to_raster(record.mask), dtype=np.uint8)
    local = raw.reshape(record.mask.height, record.mask.width) > 0
    return MaskPatch(round(record.bounds.left), round(record.bounds.top), local)


def _tracks(records: tuple, concept: str, dx: int, dy: int) -> list[Track]:
    """Latest revision per (frame, object), grouped by object id into tracks ordered by frame."""
    latest: dict[Any, SegmentationMaskRecord] = {}
    for record in records:
        if isinstance(record, SegmentationMaskRecord):
            latest[record.identity] = record
    by_object: dict[str, list[TrackFrame]] = {}
    for record in latest.values():
        index = record.frame.frame_index if record.frame is not None else 0
        frame = TrackFrame(index, _patch(record).shifted(dx, dy), record.confidence)
        by_object.setdefault(record.object_id, []).append(frame)
    return [
        Track(f"obj{object_id}", concept, tuple(sorted(frames, key=lambda f: f.index)))
        for object_id, frames in sorted(by_object.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 0)
    ]


def sam_client(settings: Settings, *, http_client: Any = None) -> AsyncOpenAI:
    """A client for SAM calls: no SDK retries (each pipeline attempt is one logged request) and a bounded wait."""
    if settings.model_api_key is None:
        raise RuntimeError("MODEL_API_KEY is not set")
    return AsyncOpenAI(
        base_url=settings.meta_base_url,
        api_key=settings.model_api_key.get_secret_value(),
        max_retries=0,
        timeout=Timeout(settings.sam_timeout_s, connect=5.0),
        http_client=http_client,
    )


def _parse(events: list[Any], mode: str, concept: str, dx: int, dy: int) -> tuple[Any, list[Track]]:
    """Parse a received stream and decode its masks. Seconds of pure-Python work for a video (about 9 s for 60
    frames), so it runs in a worker thread on its own event loop, never on the worker's."""

    async def replay() -> AsyncIterator[Any]:
        for event in events:
            yield event

    async def parse() -> Any:  # the parser needs a running loop when it is created
        format_ = image_segmentation_format() if mode == "image" else video_segmentation_format()
        return await parse_responses_stream(replay(), format_).final_result()

    result = asyncio.run(parse())
    return result.outcome, _tracks(result.records, concept, dx, dy)


async def segment(
    media: np.ndarray | Clip,
    concept: str,
    *,
    mode: Literal["image", "video"],
    settings: Settings,
    roi: tuple[float, float, float, float] | None = None,
    client: Any = None,
) -> Any:
    """Segment every instance of one concept. Returns a SegmentResult; raises SegmentError on failure."""
    from argus.segment import SegmentResult  # the result type lives with the public entry point

    _check_concept(concept)
    dx = dy = 0
    if mode == "image":
        if not isinstance(media, np.ndarray):
            raise TypeError("image mode takes a BGR image")
        image = media
        if roi is not None:
            height, width = image.shape[:2]
            x0, y0 = max(int(roi[0]), 0), max(int(roi[1]), 0)
            x1, y1 = min(int(round(roi[2])), width), min(int(round(roi[3])), height)
            image, dx, dy = image[y0:y1, x0:x1], x0, y0
        content = [{"type": "input_text", "text": concept}, {"type": "input_image", "image_url": _jpeg_url(image)}]
        metadata = METADATA
        billed = {"images": 1, "frames": 0}
        cost = settings.sam_image_usd
    else:
        if not isinstance(media, Clip):
            raise TypeError("video mode takes a Clip")
        if media.frame_count > settings.sam_max_video_frames:
            raise ValueError(f"a video request takes at most {settings.sam_max_video_frames} frames")
        content = [{"type": "input_text", "text": concept}, {"type": "input_video", "video_url": _mp4_url(media)}]
        metadata = {**METADATA, "propagation_direction": "forward"}
        frames = max(media.frame_count, settings.sam_video_min_frames)
        billed = {"images": 0, "frames": frames}
        cost = frames * settings.sam_video_frame_usd

    def call(status: Literal["ok", "error"], started: float, *, cost_usd: float, error: str | None = None):
        return ModelCallDraft(
            function="segment",
            model=settings.segment_model,
            tier="segment",
            cost_usd=cost_usd,
            latency_s=round(time.perf_counter() - started, 3),
            status=status,
            error=error,
            **billed,
        )

    started = time.perf_counter()
    responded = False
    owned = client is None  # a one-off caller without a client gets one for this call only
    try:
        client = client or sam_client(settings)
        stream = await client.responses.create(
            model=settings.segment_model,
            input=[{"type": "message", "role": "user", "content": content}],
            metadata=metadata,
            stream=True,
        )
        responded = True
        events = [event async for event in stream]
        outcome, tracks = await asyncio.to_thread(_parse, events, mode, concept, dx, dy)
    except Exception as error:  # transport, API and parser errors all mean: no masks from this call
        text = f"{type(error).__name__}: {error}"
        raise SegmentError(text, call("error", started, cost_usd=cost if responded else 0.0, error=text)) from error
    finally:
        if owned and client is not None:
            await client.close()
    if not isinstance(outcome, CompletedOutcome):
        text = f"stream incomplete: {outcome.reason} {outcome.detail or ''}".strip()
        raise SegmentError(text, call("error", started, cost_usd=cost, error=text))
    return SegmentResult(tracks, call("ok", started, cost_usd=cost))
