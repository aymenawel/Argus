"""Probe SAM 3.1 box prompts on a swarm SAM missed by name (live API, run by hand, about $0.0075; D-92).

On the swarming run (D-89, local only), a picture of the fliA 0.1 dish between 14 and 20 h where SAM found no
"microbial colony" by name: the change map against the dish's first three pictures proposes regions, and SAM is
asked (a) with one box per region and (b) with the largest region's box and its strongest point as one object. Then
(c) one box around one coin of scikit-image's `coins`, whose stream is saved as a test fixture. The swarm's pixels
and masks stay in `probes/out/` (git-ignored).

    uv run --env-file ../.env python -m probes.sam_pointed
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from meta_sam_parser import (
    SegmentationMaskRecord,
    decode_mask_to_raster,
    image_segmentation_format,
    parse_responses_stream,
)
from skimage import data

from argus.segment.change import change_reference, change_regions

from ._common import OUT, REPO, async_client, jpeg_data_url, save
from .sam import SAM_METADATA

RUN, DISH = "run_abe054d55ff3", "fliA 0.1"
MARGIN = 8  # as the import crops a vessel for SAM
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sam"


def padded(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    """A region's box (x1, y1 exclusive) padded by 15% of its size on each side, clipped, x2 and y2 inclusive."""
    x0, y0, x1, y1 = box
    dx, dy = round(0.15 * (x1 - x0)), round(0.15 * (y1 - y0))
    return max(x0 - dx, 0), max(y0 - dy, 0), min(x1 + dx, width) - 1, min(y1 + dy, height) - 1


def box_token(box: tuple[int, int, int, int], width: int, height: int) -> str:
    x1, y1, x2, y2 = box
    return f"<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={width};h={height}|>"


async def ask(image: np.ndarray, text: str) -> tuple[list[dict], dict]:
    """One image request; the raw events and what came back."""
    started = time.perf_counter()
    try:
        stream = await async_client().responses.create(
            model=os.environ["SEGMENT_MODEL"],
            input=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": text},
                        {"type": "input_image", "image_url": jpeg_data_url(image)},
                    ],
                }
            ],
            metadata=SAM_METADATA,
            stream=True,
        )
        events = [event.model_dump(mode="json") async for event in stream]
    except Exception as error:  # a refused prompt is an answer here
        return [], {"text": text, "error": f"{type(error).__name__}: {error}"}
    latency = round(time.perf_counter() - started, 2)

    async def replay() -> AsyncIterator[Any]:
        for event in events:
            yield event

    result = await parse_responses_stream(replay(), image_segmentation_format()).final_result()
    masks = [r for r in result.records if isinstance(r, SegmentationMaskRecord)]
    return events, {
        "text": text,
        "outcome": type(result.outcome).__name__,
        "latency_s": latency,
        "objects": [
            {
                "object_id": r.object_id,
                "bounds": [round(r.bounds.left), round(r.bounds.top), r.mask.width, r.mask.height],
                "area_px": int(np.frombuffer(decode_mask_to_raster(r.mask), np.uint8).astype(bool).sum()),
                "confidence": r.confidence,
            }
            for r in masks
        ],
    }


def crop_of(path: str, roi: list) -> tuple[np.ndarray, np.ndarray]:
    image = cv2.imread(str(REPO / "data" / path))
    h, w = image.shape[:2]
    points = np.asarray(roi, np.float64)
    x0, y0 = (np.floor(points.min(axis=0)).astype(int) - MARGIN).clip(0)
    x1, y1 = np.ceil(points.max(axis=0)).astype(int) + MARGIN
    x1, y1 = min(int(x1), w), min(int(y1), h)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [np.round(points - (x0, y0)).astype(np.int32)], 1)
    return image[y0:y1, x0:x1], mask.astype(bool)


async def main() -> None:
    db = sqlite3.connect(f"file:{REPO / 'data' / 'argus.sqlite'}?mode=ro", uri=True)
    vessel_id, roi = db.execute("SELECT id, roi FROM vessels WHERE run_id=? AND label=?", (RUN, DISH)).fetchone()
    roi = json.loads(roi)
    first = [p for (p,) in db.execute("SELECT path FROM frames WHERE run_id=? ORDER BY t LIMIT 3", (RUN,))]
    missed = db.execute(
        "SELECT f.t, f.path FROM sam_answers a JOIN frames f ON f.id = a.frame_id WHERE a.run_id=? AND a.vessel_id=? "
        "AND a.found=0 AND f.t BETWEEN ? AND ? ORDER BY f.t",
        (RUN, vessel_id, 14 * 3600, 20 * 3600),
    ).fetchall()
    t, path = missed[len(missed) // 2]
    crops = [crop_of(p, roi) for p in first]
    reference = change_reference([c for c, _ in crops], crops[0][1], roi)
    crop, _ = crop_of(path, roi)
    regions = change_regions(reference, crop)
    height, width = crop.shape[:2]
    lab_now = cv2.cvtColor(crop.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    delta = np.sqrt(((lab_now - reference.lab) ** 2).sum(axis=2))
    overlay = crop.copy()
    for region in regions:
        contours, _ = cv2.findContours(region.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 0, 255), 2)
        x1, y1, x2, y2 = padded(region.box, width, height)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), 1)
    cv2.imwrite(str(OUT / "pointed_regions.png"), np.hstack([crop, overlay]))
    found = {
        "frame_t_h": round(t / 3600, 2),
        "crop": [width, height],
        "noise_dE": round(reference.noise, 3),
        "vessel_px": int(reference.inside.sum()),
        "regions": [
            {"area_px": int(r.mask.sum()), "box": list(r.box), "median_dE": round(float(np.median(delta[r.mask])), 2)}
            for r in regions
        ],
    }
    calls: dict[str, Any] = {}
    if regions:
        boxes = ",".join(
            f"{i}{box_token(padded(r.box, width, height), width, height)}" for i, r in enumerate(regions, start=1)
        )
        _, calls["a_boxes"] = await ask(crop, f"<0f>{boxes}")
        largest = regions[0]
        px, py = largest.peak
        point = f"<|point;x={px};y={py};w={width};h={height}|>"
        _, calls["b_box_and_point"] = await ask(
            crop, f"<0f>1{box_token(padded(largest.box, width, height), width, height)}{point}"
        )
    coins = cv2.cvtColor(data.coins(), cv2.COLOR_GRAY2BGR)
    grey = data.coins()
    _, binary = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (
        int(stats[biggest, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT)
    )
    coin_box = (x, y, x + w - 1, y + h - 1)
    events, calls["c_coin_box"] = await ask(coins, f"<0f>1{box_token(coin_box, 384, 303)}")
    if events:
        FIXTURES.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(e, separators=(",", ":")) for e in events]
        (FIXTURES / "image_pointed.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    calls["c_coin_box"]["box"] = list(coin_box)
    save("sam_pointed", {"change_map": found, "calls": calls})


if __name__ == "__main__":
    asyncio.run(main())
