"""reason(): Muse Spark (routine) and Muse Wonder (deep) over the Responses API, with strict JSON (spec §7.1).
The routine tier can run on Muse Spark Open, Meta's open-weight model served by Baseten, falling back to Muse Spark
on Meta when Baseten fails (D-77).

Only this package and argus.segment call models. Prompts come from prompts/ (argus.reason.prompts); every call
returns or raises with its ModelCallDraft so the caller logs it against the run.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from argus.config import Settings
from argus.domain import ModelCallDraft
from argus.reason.client import ReasonError, Tier, call_model, image_part, open_client, reason_client

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
    open_client: Any = None,
    provider: str = "meta",
) -> ReasonResult:
    """One strict-JSON call. On the deep tier a failure is retried once on the fallback model at high effort; on the
    routine tier with provider "baseten" it goes to Muse Spark Open, and a failure there is retried once on Muse Spark
    on Meta. The result says when it fell back (spec §7.1). Raises ReasonError when nothing usable came back."""
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
        if tier == "routine" and provider == "baseten" and open_client is not None:
            try:
                model = settings.open_model
                data, call = await call_model(
                    open_client,
                    model=model,
                    effort=settings.routine_effort,
                    max_output=settings.routine_max_output,
                    **common,
                )
                return ReasonResult(data, call, model, fell_back=False)
            except ReasonError as failure:
                model = settings.routine_model
                data, call = await call_model(
                    client,
                    model=model,
                    effort=settings.routine_effort,
                    max_output=settings.routine_max_output,
                    **common,
                )
                return ReasonResult(data, call, model, fell_back=True, failed_calls=(failure.call,))
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
    """The worker's reasoning access: one client per provider for every run, closed when the worker stops.
    `provider` says, at each call, where the routine tier runs (the app's switch); Baseten needs its key."""

    def __init__(self, settings: Settings, provider: Callable[[], str] | None = None) -> None:
        self.settings = settings
        self.provider = provider or (lambda: settings.routine_provider)
        self._client: Any = None
        self._open_client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = reason_client(self.settings)
        return self._client

    @property
    def open_client(self) -> Any:
        if self._open_client is None:
            self._open_client = open_client(self.settings)
        return self._open_client

    def current_provider(self) -> str:
        choice = self.provider()
        return "baseten" if choice == "baseten" and self.settings.baseten_api_key is not None else "meta"

    async def __call__(
        self, task: ReasonTask, *, tier: Tier, schema: dict, schema_name: str, images: Sequence[bytes] = ()
    ) -> ReasonResult:
        provider = self.current_provider() if tier == "routine" else "meta"
        return await reason(
            task,
            tier=tier,
            schema=schema,
            schema_name=schema_name,
            images=images,
            settings=self.settings,
            client=self.client,
            open_client=self.open_client if provider == "baseten" else None,
            provider=provider,
        )

    async def aclose(self) -> None:
        for client in (self._client, self._open_client):
            if client is not None:
                await client.close()
