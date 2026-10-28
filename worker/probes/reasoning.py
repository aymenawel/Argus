"""Probe Muse Spark 1.3 and Muse Wonder 1.0 on the Responses API.

Checks: image token cost at two snapshot sizes, automatic prompt caching on a repeated call,
strict JSON output with prompts/schemas/note.json and verdict_critique.json, and a first
claim check of the note's numbers. Snapshots and measurements come from probes.sam
(the coins photograph and code-computed mask areas), so run that probe first.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from typing import Any

import cv2

from ._common import OUT, REPO, client, jpeg_data_url, load_prompt, load_schema, resize_long_side, save, usage_row

SPARK = os.environ["REASONING_ROUTINE_MODEL"]
WONDER = os.environ["REASONING_DEEP_MODEL"]
RULES = load_prompt("system/scientific-rules.md")


def _snapshots(long_side: int) -> list[dict[str, str]]:
    images = [cv2.imread(str(OUT / name)) for name in ("coins.jpg", "coins_masks.png")]
    return [{"type": "input_image", "image_url": jpeg_data_url(resize_long_side(i, long_side))} for i in images]


def _call(model: str, content: list[dict[str, Any]], instructions: str, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
    started = time.perf_counter()
    response = client().responses.create(
        model=model,
        instructions=instructions,
        input=[{"type": "message", "role": "user", "content": content}],
        **kwargs,
    )
    return response, usage_row(model, response.usage, time.perf_counter() - started)


def probe_image_tokens() -> list[dict[str, Any]]:
    """Two snapshots per call; the 768 px call is repeated to check prompt caching."""
    rows = []
    question = {
        "type": "input_text",
        "text": (
            "Snapshot 1 is a frame, snapshot 2 shows its segmentation outlines. "
            "In one sentence, do the outlines follow the objects?"
        ),
    }
    for model in (SPARK, WONDER):
        for long_side, attempt in ((1280, 1), (768, 1), (768, 2)):
            response, row = _call(
                model, [question, *_snapshots(long_side)], RULES, reasoning={"effort": "low"}, max_output_tokens=600
            )
            rows.append({**row, "snapshot_long_side_px": long_side, "attempt": attempt, "text": response.output_text})
    counted = client().responses.input_tokens.count(
        model=SPARK,
        instructions=RULES,
        input=[{"type": "message", "role": "user", "content": [question, *_snapshots(768)]}],
    )
    rows.append({"input_tokens_count_endpoint_768px": counted.input_tokens})
    return rows


def _measurements() -> list[dict[str, Any]]:
    """Real numbers computed in code from the SAM probe's masks (pixels; no calibration card here)."""
    sam = json.loads((OUT / "sam_image.json").read_text())
    areas = sam["mask_area_px"]
    return [
        {"id": "m1", "metric": "object_count", "value": len(areas), "unit": "count"},
        {"id": "m2", "metric": "mean_mask_area", "value": round(statistics.mean(areas)), "unit": "px^2"},
        {"id": "m3", "metric": "sd_mask_area", "value": round(statistics.stdev(areas)), "unit": "px^2"},
        {"id": "m4", "metric": "largest_mask_area", "value": max(areas), "unit": "px^2"},
    ]


NUMBER = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")


def _claim_check(note: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every cited number must match its measurement row; every number in the prose must be a known value."""
    by_id = {r["id"]: r for r in rows}
    cited_errors = [
        n
        for n in note["numbers_used"]
        if n["measurement_id"] not in by_id or abs(by_id[n["measurement_id"]]["value"] - n["value"]) > 1e-6
    ]
    allowed = {float(r["value"]) for r in rows}
    prose = " ".join(
        note[k] for k in ("observation", "interpretation", "next_step", "question_for_researcher", "confidence_reason")
    )
    prose_numbers = [float(x.replace(",", "")) for x in NUMBER.findall(prose)]
    unknown = [x for x in prose_numbers if x not in allowed and x not in (1.0, 2.0)]  # small ordinals allowed for now
    return {
        "cited_mismatches": cited_errors,
        "prose_numbers": prose_numbers,
        "unknown_prose_numbers": unknown,
        "passed": not cited_errors and not unknown,
    }


def probe_cache() -> list[dict[str, Any]]:
    """Repeat calls with a long stable text prefix (~2.5k tokens), with and without prompt_cache_key."""
    prefix = (
        RULES
        + "\n\n"
        + load_prompt("deep/verdict-critique.md")
        + "\n\n"
        + (REPO / "docs/knowledge-base/08-science-rigor.md").read_text(encoding="utf-8")
    )
    question = [{"type": "input_text", "text": "Reply with the single word: ready."}]
    rows = []
    for label, extra in (
        ("no_key", {}),
        ("cache_key", {"prompt_cache_key": "argus-probe-rules"}),
        ("cache_key_24h", {"prompt_cache_key": "argus-probe-rules-24h", "prompt_cache_retention": "24h"}),
    ):
        for attempt in (1, 2, 3):
            _, row = _call(SPARK, question, prefix, reasoning={"effort": "minimal"}, max_output_tokens=300, **extra)
            rows.append({"variant": label, "attempt": attempt, **row})
            time.sleep(2)
    for attempt in (1, 2):
        _, row = _call(
            SPARK,
            [*_snapshots(768), *question],
            prefix,
            reasoning={"effort": "minimal"},
            max_output_tokens=300,
            prompt_cache_key="argus-probe-images",
        )
        rows.append({"variant": "cache_key_with_images", "attempt": attempt, **row})
        time.sleep(2)
    return rows


def probe_note_json() -> list[dict[str, Any]]:
    rows = _measurements()
    block = "MEASUREMENTS (probe: one frame of the coins photograph, segmented by SAM 3.1 with the concept 'coin')\n"
    block += "\n".join(f"{r['id']} {r['metric']} = {r['value']} {r['unit']}" for r in rows)
    content = [{"type": "input_text", "text": block + "\n\nWrite one event note about this frame."}, *_snapshots(768)]
    results = []
    for effort in ("minimal", "low"):
        response, row = _call(
            SPARK,
            content,
            RULES,
            reasoning={"effort": effort},
            max_output_tokens=4000,
            text={
                "format": {"type": "json_schema", "name": "ArgusNote", "schema": load_schema("note"), "strict": True}
            },
        )
        note = json.loads(response.output_text)
        results.append({"effort": effort, **row, "note": note, "claim_check": _claim_check(note, rows)})
    return results


def probe_critique_json() -> dict[str, Any]:
    """Schema test on the deep tier with a deliberately flawed, clearly synthetic draft verdict."""
    draft = (
        "SYNTHETIC SCHEMA TEST (not real data).\n"
        "Plan (locked): Hypothesis: warm water makes yeast foam rise faster. Prediction: warm jar reaches 30 mm foam "
        "at least 10 min sooner than the room-temperature jar. Threshold: 10 min.\n"
        "Design: 1 warm jar, 1 room-temperature jar, no replicates. Noise floor of height: 0.8 mm.\n"
        "MEASUREMENTS: s1 warm time_to_30mm = 14 min; s2 control time_to_30mm = 22 min; "
        "s3 difference = 8 min; e1 lamp switched on at 12 min (logged intervention).\n"
        "Draft verdict: SUPPORTED. Warm water proves faster rising; 120 frames of the warm jar all agree."
    )
    response, row = _call(
        WONDER,
        [{"type": "input_text", "text": draft}],
        RULES + "\n\n" + load_prompt("deep/verdict-critique.md"),
        reasoning={"effort": "medium"},
        max_output_tokens=4000,
        text={
            "format": {
                "type": "json_schema",
                "name": "VerdictCritique",
                "schema": load_schema("verdict_critique"),
                "strict": True,
            }
        },
    )
    return {**row, "critique": json.loads(response.output_text)}


PROBES = {
    "image_tokens": probe_image_tokens,
    "cache": probe_cache,
    "note": probe_note_json,
    "critique": probe_critique_json,
}


def main() -> None:
    selected = sys.argv[1:] or list(PROBES)
    for name in selected:
        save(f"reasoning_{name}", PROBES[name]())


if __name__ == "__main__":
    main()
