"""Probe SAM 3.1 image and video segmentation and parse the stream with meta-sam-parser.

Test media: scikit-image's bundled `coins` photograph (24 coins), plus a short H.264 clip
made by panning a window across it. The clip's motion is synthetic; it checks the video
request shape, parsing, object IDs and billing, not tracking quality on real experiments.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any

import cv2
import numpy as np
from meta_sam_parser import (
    SegmentationMaskRecord,
    decode_mask_to_raster,
    decode_mask_to_svg_path,
    image_segmentation_format,
    parse_responses_stream,
    video_segmentation_format,
)
from skimage import data

from ._common import OUT, async_client, file_data_url, jpeg_data_url, save

SAM_METADATA = {"mask_encoding": "one_bit", "include_confidence": "true"}


async def _capture_events(stream: AsyncIterator[Any], seen: dict[str, Any]) -> AsyncIterator[Any]:
    """Pass events through to the parser while keeping event types and the final response."""
    async for event in stream:
        seen.setdefault("event_types", set()).add(event.type)
        if getattr(event, "response", None) is not None:
            seen["response"] = event.response
        yield event


async def _segment(content: list[dict[str, Any]], video: bool) -> tuple[Any, dict[str, Any], float]:
    started = time.perf_counter()
    stream = await async_client().responses.create(
        model=os.environ["SEGMENT_MODEL"],
        input=[{"type": "message", "role": "user", "content": content}],
        metadata=SAM_METADATA,
        stream=True,
    )
    seen: dict[str, Any] = {}
    format_ = video_segmentation_format() if video else image_segmentation_format()
    result = await parse_responses_stream(_capture_events(stream, seen), format_).final_result()
    return result, seen, time.perf_counter() - started


def _mask_to_canvas(record: SegmentationMaskRecord, height: int, width: int) -> np.ndarray:
    """Place a box-local one-bit mask into a full-frame boolean array."""
    local = np.frombuffer(decode_mask_to_raster(record.mask), dtype=np.uint8)
    local = local.reshape(record.mask.height, record.mask.width) > 0
    left, top = round(record.bounds.left), round(record.bounds.top)
    canvas = np.zeros((height, width), dtype=bool)
    h = min(local.shape[0], height - top)
    w = min(local.shape[1], width - left)
    canvas[top : top + h, left : left + w] = local[:h, :w]
    return canvas


def _response_summary(seen: dict[str, Any]) -> dict[str, Any]:
    response = seen.get("response")
    usage = getattr(response, "usage", None)
    return {
        "event_types": sorted(seen.get("event_types", [])),
        "status": getattr(response, "status", None),
        "usage": usage.model_dump() if usage is not None else None,
    }


async def probe_image() -> None:
    image = cv2.cvtColor(data.coins(), cv2.COLOR_GRAY2BGR)
    height, width = image.shape[:2]
    cv2.imwrite(str(OUT / "coins.jpg"), image)

    result, seen, latency = await _segment(
        [{"type": "input_text", "text": "coin"}, {"type": "input_image", "image_url": jpeg_data_url(image)}],
        video=False,
    )
    masks = [r for r in result.records if isinstance(r, SegmentationMaskRecord)]
    areas = []
    overlay = image.copy()
    for record in masks:
        canvas = _mask_to_canvas(record, height, width)
        areas.append(int(canvas.sum()))
        contours, _ = cv2.findContours(canvas.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (163, 163, 15), 1)
    cv2.imwrite(str(OUT / "coins_masks.png"), overlay)

    save(
        "sam_image",
        {
            "image_size": [width, height],
            "concept": "coin",
            "expected_count": 24,
            "instances": len(masks),
            "record_kinds": sorted({r.kind for r in result.records}),
            "confidences": [round(r.confidence, 3) for r in masks if r.confidence is not None],
            "mask_area_px": areas,
            "mask_size_vs_bounds": [
                [
                    r.mask.width,
                    r.mask.height,
                    round(r.bounds.right - r.bounds.left),
                    round(r.bounds.bottom - r.bounds.top),
                ]
                for r in masks[:3]
            ],
            "svg_path_example": decode_mask_to_svg_path(masks[0].mask)[:160] if masks else None,
            "diagnostics": [str(d) for d in result.diagnostics],
            "outcome": str(result.outcome),
            "latency_s": round(latency, 2),
            "cost_usd": 0.0025,
            **_response_summary(seen),
        },
    )


def _make_pan_clip(frames: int = 60, fps: int = 10) -> Any:
    """Write a short H.264 MP4 that pans a 240x240 window across the coins photo."""
    image = cv2.cvtColor(data.coins(), cv2.COLOR_GRAY2BGR)
    frame_dir = OUT / "pan_frames"
    frame_dir.mkdir(exist_ok=True)
    for i in range(frames):
        x, y = 20 + i, 10 + i // 2
        cv2.imwrite(str(frame_dir / f"{i:04d}.png"), image[y : y + 240, x : x + 240])
    clip = OUT / "pan.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(frame_dir / "%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        check=True,
    )
    return clip


async def probe_video() -> None:
    clip = _make_pan_clip()
    result, seen, latency = await _segment(
        [
            {"type": "input_text", "text": "coin"},
            {"type": "input_video", "video_url": file_data_url(clip, "video/mp4")},
        ],
        video=True,
    )
    masks = [r for r in result.records if isinstance(r, SegmentationMaskRecord)]
    frames = sorted({r.frame.frame_index for r in masks if r.frame is not None})
    ids_per_frame: dict[int, list[str]] = {}
    for record in masks:
        if record.frame is not None:
            ids_per_frame.setdefault(record.frame.frame_index, []).append(record.object_id)
    first, last = (ids_per_frame[frames[0]], ids_per_frame[frames[-1]]) if frames else ([], [])
    save(
        "sam_video",
        {
            "clip_frames": 60,
            "concept": "coin",
            "frames_with_masks": len(frames),
            "mask_records": len(masks),
            "distinct_object_ids": len({r.object_id for r in masks}),
            "ids_first_frame": sorted(first, key=int),
            "ids_last_frame": sorted(last, key=int),
            "ids_kept_first_to_last": len(set(first) & set(last)),
            "diagnostics": [str(d) for d in result.diagnostics],
            "outcome": str(result.outcome),
            "latency_s": round(latency, 2),
            "cost_usd_at_50_frame_minimum": round(max(60, 50) * 0.20 / 1000, 4),
            **_response_summary(seen),
        },
    )


async def main() -> None:
    await probe_image()
    await probe_video()


if __name__ == "__main__":
    asyncio.run(main())
