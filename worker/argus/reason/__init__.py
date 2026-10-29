"""reason(): Muse Spark (routine) and Muse Wonder (deep) over the Responses API, with strict JSON (spec §7.1).

Only this package and argus.segment call models. Prompts come from prompts/ (argus.reason.prompts); every call
returns or raises with its ModelCallDraft so the caller logs it against the run.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from argus.config import Settings
from argus.domain import ModelCallDraft
from argus.reason.client import ReasonError, Tier, call_model, image_part, reason_client

__all__ = ["ReasonError", "ReasonResult", "ReasonTask", "Reasoner", "SettingsReasoner", "reason", "reason_client"]


@dataclass(frozen=True)
class ReasonTask:
    """What to send, split for prompt caching: `stable` parts (rules, method card, locked plan) come first and are
    identical across a run's calls; `variable` parts (summary, MEASUREMENTS, events, notes, the task) follow."""

    function: str
    experiment_id: str
    prompt_version: str
    stable: tuple[str, ...]
    variable: tuple[str, ...]


@dataclass(frozen=True)
class ReasonResult:
    data: dict[str, Any]
    call: ModelCallDraft
    model: str
    fell_back: bool
    failed_calls: tuple[ModelCallDraft, ...] = ()  # a deep call that fell back: its failed first attempt


async def reason(
    task: ReasonTask,
    *,
    tier: Tier,
    schema: dict,
    schema_name: str,
    images: Sequence[bytes] = (),
    settings: Settings,
    client: Any = None,
) -> ReasonResult:
    """One strict-JSON call. On the deep tier a failure is retried once on the fallback model at high effort,
    and the result says so (spec §7.1). Raises ReasonError when nothing usable came back."""
    owned = client is None
    client = client or reason_client(settings)
    content = [{"type": "input_text", "text": part} for part in (*task.stable, *task.variable)]
    content += [image_part(jpeg) for jpeg in images]
    cache_key = f"argus:{task.experiment_id}:{tier}:{task.prompt_version}"
    common = dict(
        function=task.function,
        tier=tier,
        cache_key=cache_key,
        content=content,
        schema=schema,
        schema_name=schema_name,
        settings=settings,
    )
    try:
        if tier == "routine":
            model = settings.routine_model
            data, call = await call_model(
                client, model=model, effort=settings.routine_effort, max_output=settings.routine_max_output, **common
            )
            return ReasonResult(data, call, model, fell_back=False)
        try:
            model = settings.deep_model
            data, call = await call_model(
                client, model=model, effort=settings.deep_effort, max_output=settings.deep_max_output, **common
            )
            return ReasonResult(data, call, model, fell_back=False)
        except ReasonError as failure:
            model = settings.deep_fallback_model
            data, call = await call_model(
                client, model=model, effort=settings.fallback_effort, max_output=settings.deep_max_output, **common
            )
            return ReasonResult(data, call, model, fell_back=True, failed_calls=(failure.call,))
    finally:
        if owned:
            await client.close()


class Reasoner(Protocol):
    async def __call__(
        self, task: ReasonTask, *, tier: Tier, schema: dict, schema_name: str, images: Sequence[bytes] = ()
    ) -> ReasonResult: ...


class SettingsReasoner:
    """The worker's reasoning access: one client for every run, closed when the worker stops."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = reason_client(self.settings)
        return self._client

    async def __call__(
        self, task: ReasonTask, *, tier: Tier, schema: dict, schema_name: str, images: Sequence[bytes] = ()
    ) -> ReasonResult:
        return await reason(
            task,
            tier=tier,
            schema=schema,
            schema_name=schema_name,
            images=images,
            settings=self.settings,
            client=self.client,
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
