"""Live updates for the web app as server-sent events.

Events get increasing ids and are kept in a short history, so a browser that reconnects with
Last-Event-ID receives what it missed. Publishing is safe from any thread (capture runs in threads).
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ServerEvent:
    id: int
    type: str
    data: dict


class EventBroker:
    def __init__(self, history: int = 500) -> None:
        self._lock = threading.Lock()
        self._history: deque[ServerEvent] = deque(maxlen=history)
        self._last_id = 0
        self._subscribers: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[ServerEvent]]] = set()

    def publish(self, type: str, data: Mapping) -> ServerEvent:
        with self._lock:
            self._last_id += 1
            event = ServerEvent(self._last_id, type, dict(data))
            self._history.append(event)
            subscribers = list(self._subscribers)
        for loop, queue in subscribers:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:  # the subscriber's loop has closed
                self._unregister((loop, queue))
        return event

    def since(self, last_id: int) -> list[ServerEvent]:
        with self._lock:
            return [e for e in self._history if e.id > last_id]

    def _register(self) -> tuple[asyncio.AbstractEventLoop, asyncio.Queue[ServerEvent]]:
        entry = (asyncio.get_running_loop(), asyncio.Queue())
        with self._lock:
            self._subscribers.add(entry)
        return entry

    def _unregister(self, entry: tuple[asyncio.AbstractEventLoop, asyncio.Queue[ServerEvent]]) -> None:
        with self._lock:
            self._subscribers.discard(entry)

    async def subscribe(self) -> AsyncIterator[ServerEvent]:
        entry = self._register()
        try:
            while True:
                yield await entry[1].get()
        finally:
            self._unregister(entry)


def format_sse(event: ServerEvent) -> str:
    data = json.dumps(event.data, separators=(",", ":"), ensure_ascii=False)
    return f"id: {event.id}\nevent: {event.type}\ndata: {data}\n\n"


async def event_stream(
    broker: EventBroker, last_event_id: int | None, *, heartbeat_s: float = 15.0
) -> AsyncIterator[str]:
    """Replay what the client missed, then stream new events, with a keep-alive comment while idle."""
    entry = broker._register()  # register before replaying so nothing published in between is lost
    try:
        last_sent = last_event_id or 0
        if last_event_id is not None:
            for event in broker.since(last_event_id):
                last_sent = event.id
                yield format_sse(event)
        while True:
            try:
                event = await asyncio.wait_for(entry[1].get(), heartbeat_s)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if event.id > last_sent:
                last_sent = event.id
                yield format_sse(event)
    finally:
        broker._unregister(entry)
