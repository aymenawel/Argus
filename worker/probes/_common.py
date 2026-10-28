"""Shared helpers for the day-one probes."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from openai import AsyncOpenAI, OpenAI

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# USD per 1M tokens (docs/knowledge-base/05-costs-and-credits.md, checked Oct 27, 2026).
TOKEN_PRICES = {
    "muse-spark-1.3": {"input": 1.25, "cached": 0.15, "output": 4.25},
    "muse-wonder-1.0": {"input": 4.00, "cached": 0.20, "output": 20.00},
}


def client() -> OpenAI:
    return OpenAI(base_url=os.environ["META_BASE_URL"], api_key=os.environ["MODEL_API_KEY"])


def async_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=os.environ["META_BASE_URL"], api_key=os.environ["MODEL_API_KEY"])


def resize_long_side(image: np.ndarray, long_side: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = long_side / max(height, width)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=interpolation)


def jpeg_data_url(image: np.ndarray, quality: int = 90) -> str:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG encoding failed")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode()


def file_data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def usage_row(model: str, usage: Any, latency_s: float) -> dict[str, Any]:
    """Token counts and cost for one Responses API call (cached tokens are part of input)."""
    input_tokens = usage.input_tokens
    cached = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0
    output_tokens = usage.output_tokens
    reasoning = getattr(usage.output_tokens_details, "reasoning_tokens", 0) or 0
    price = TOKEN_PRICES[model]
    cost = ((input_tokens - cached) * price["input"] + cached * price["cached"] + output_tokens * price["output"]) / 1e6
    return {
        "model": model,
        "input_tokens": input_tokens,
        "cached_tokens": cached,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning,
        "cost_usd": round(cost, 6),
        "latency_s": round(latency_s, 2),
    }


def load_schema(name: str) -> dict[str, Any]:
    """Load a JSON output schema from prompts/schemas/, dropping the non-standard `$comment`."""
    schema = json.loads((REPO / "prompts" / "schemas" / f"{name}.json").read_text(encoding="utf-8"))
    schema.pop("$comment", None)
    return schema


def load_prompt(relative_path: str) -> str:
    return (REPO / "prompts" / relative_path).read_text(encoding="utf-8")


def save(name: str, data: Any) -> None:
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(json.dumps(data, indent=2, default=str))
    print(f"-> saved {path.relative_to(REPO)}")
