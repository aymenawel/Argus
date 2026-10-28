"""Record raw SAM 3.1 response streams as test fixtures (live API, run by hand, about $0.02).

Each stream event is saved as one JSON line, so tests can replay a real response through the parser
without the network. Media: scikit-image's `coins` photo (concept `coin`, 24 coins) and the 60-frame
pan clip from `probes/sam.py`.

    uv run --env-file ../.env python -m probes.record_sam
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import cv2
from skimage import data

from ._common import async_client, file_data_url, jpeg_data_url
from .sam import SAM_METADATA, _make_pan_clip

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sam"


async def _record(name: str, content: list[dict]) -> int:
    stream = await async_client().responses.create(
        model=os.environ["SEGMENT_MODEL"],
        input=[{"type": "message", "role": "user", "content": content}],
        metadata=SAM_METADATA,
        stream=True,
    )
    lines = [json.dumps(event.model_dump(mode="json"), separators=(",", ":")) async for event in stream]
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / f"{name}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


async def main() -> None:
    image = cv2.cvtColor(data.coins(), cv2.COLOR_GRAY2BGR)
    image_events = await _record(
        "coins-image",
        [{"type": "input_text", "text": "coin"}, {"type": "input_image", "image_url": jpeg_data_url(image)}],
    )
    clip = _make_pan_clip()
    video_events = await _record(
        "pan-video",
        [
            {"type": "input_text", "text": "coin"},
            {"type": "input_video", "video_url": file_data_url(clip, "video/mp4")},
        ],
    )
    print(f"coins-image.jsonl: {image_events} events; pan-video.jsonl: {video_events} events -> {FIXTURES}")


if __name__ == "__main__":
    asyncio.run(main())
