"""The one Responses API call behind reason(): request, usage → cost, and the model-call record.

This and argus/segment/sam.py are the only modules that import the model SDK (spec §7.1).
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Sequence
from typing import Any, Literal

from openai import AsyncOpenAI, Timeout

from argus.config import Settings
from argus.domain import ModelCallDraft

Tier = Literal["routine", "deep"]


class ReasonError(RuntimeError):
    """A reasoning call that gave nothing usable, carrying the model call to log (status "error")."""

    def __init__(self, message: str, call: ModelCallDraft) -> None:
        super().__init__(message)
        self.call = call


def reason_client(settings: Settings, *, http_client: Any = None) -> AsyncOpenAI:
    """No SDK retries (each attempt is one logged request) and a bounded wait, as for SAM."""
    if settings.model_api_key is None:
        raise RuntimeError("MODEL_API_KEY is not set")
    return AsyncOpenAI(
        base_url=settings.meta_base_url,
        api_key=settings.model_api_key.get_secret_value(),
        max_retries=0,
        timeout=Timeout(settings.reason_timeout_s, connect=5.0),
        http_client=http_client,
    )


def open_client(settings: Settings, *, http_client: Any = None) -> AsyncOpenAI:
    """Baseten's endpoint for Muse Spark Open, set up like Meta's: no SDK retries, a bounded wait."""
    if settings.baseten_api_key is None:
        raise RuntimeError("BASETEN_API_KEY is not set")
    return AsyncOpenAI(
        base_url=settings.baseten_base_url,
        api_key=settings.baseten_api_key.get_secret_value(),
        max_retries=0,
        timeout=Timeout(settings.reason_timeout_s, connect=5.0),
        http_client=http_client,
    )


def _prices(settings: Settings, model: str) -> tuple[float, float, float]:
    if model == settings.deep_model:
        return settings.wonder_input_usd, settings.wonder_cached_usd, settings.wonder_output_usd
    if model == settings.open_model:
        return settings.open_input_usd, settings.open_cached_usd, settings.open_output_usd
    return settings.spark_input_usd, settings.spark_cached_usd, settings.spark_output_usd


def _usage(usage: Any) -> tuple[int, int, int, int]:
    if usage is None:
        return 0, 0, 0, 0
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", None) or 0
    reasoning = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", None) or 0
    return usage.input_tokens or 0, cached, usage.output_tokens or 0, reasoning


async def call_model(
    client: Any,
    *,
    function: str,
    tier: Tier,
    model: str,
    effort: str,
    max_output: int,
    cache_key: str,
    content: Sequence[dict[str, Any]],
    schema: dict,
    schema_name: str,
    settings: Settings,
) -> tuple[dict[str, Any], ModelCallDraft]:
    """One request. Returns the parsed JSON and the call record; raises ReasonError with the record otherwise."""
    images = sum(1 for part in content if part["type"] == "input_image")
    started = time.perf_counter()

    def record(status: Literal["ok", "error"], usage: Any = None, error: str | None = None) -> ModelCallDraft:
        fresh_and_cached, cached, output, reasoning = _usage(usage)
        prices = _prices(settings, model)
        cost = ((fresh_and_cached - cached) * prices[0] + cached * prices[1] + output * prices[2]) / 1e6
        return ModelCallDraft(
            function=function,
            model=model,
            tier=tier,
            input_tokens=fresh_and_cached,
            cached_tokens=cached,
            output_tokens=output,
            reasoning_tokens=reasoning,
            images=images,
            cost_usd=cost,
            latency_s=round(time.perf_counter() - started, 3),
            cache_key=cache_key,
            status=status,
            error=error,
        )

    try:
        response = await client.responses.create(
            model=model,
            input=[{"type": "message", "role": "user", "content": list(content)}],
            reasoning={"effort": effort},
            max_output_tokens=max_output,
            prompt_cache_key=cache_key,
            text={"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
        )
    except Exception as error:  # transport and API errors: nothing came back, nothing was billed
        text = f"{type(error).__name__}: {error}"
        raise ReasonError(text, record("error", error=text)) from error
    if response.status != "completed":
        reason = getattr(response.incomplete_details, "reason", None) or response.status
        text = f"response {response.status}: {reason}"
        raise ReasonError(text, record("error", response.usage, text))  # billed even though unusable
    try:
        data = json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError) as error:
        text = f"the answer is not JSON: {error}"
        raise ReasonError(text, record("error", response.usage, text)) from error
    if not isinstance(data, dict):
        text = "the answer is not a JSON object"
        raise ReasonError(text, record("error", response.usage, text))
    return data, record("ok", response.usage)


def image_part(jpeg: bytes) -> dict[str, str]:
    return {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")}
