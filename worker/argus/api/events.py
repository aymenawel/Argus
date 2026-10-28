"""Live updates for the web app as server-sent events.

Events get increasing ids and are kept in a short history, so a browser that reconnects with
Last-Event-ID receives what it missed. On the wire an id is "<boot>-<n>": the boot token changes each time
the worker starts, so a browser holding an id from an earlier start (or one older than the history) is told
to `resync` and reload what it shows, instead of silently missing events. Publishing is safe from any
thread (capture runs in threads).
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
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
        self.boot = uuid.uuid4().hex[:8]
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

    @property
    def last_id(self) -> int:
        with self._lock:
            return self._last_id

    def resume(self, wire_id: str) -> tuple[int, list[ServerEvent]] | None:
        """Where a client with this Last-Event-ID left off and what it missed, or None if it must resync."""
        boot, _, number = wire_id.rpartition("-")
        if boot != self.boot or not number.isdigit():
            return None
        last = int(number)
        with self._lock:
            oldest = self._history[0].id if self._history else self._last_id + 1
            if last > self._last_id or last + 1 < oldest:
                return None
            return last, [e for e in self._history if e.id > last]

    def _register(self) -> tuple[tuple[asyncio.AbstractEventLoop, asyncio.Queue[ServerEvent]], int]:
        """Add a subscriber, with the last id published before it: everything after arrives in its queue."""
        entry = (asyncio.get_running_loop(), asyncio.Queue())
        with self._lock:
            self._subscribers.add(entry)
            return entry, self._last_id

    def _unregister(self, entry: tuple[asyncio.AbstractEventLoop, asyncio.Queue[ServerEvent]]) -> None:
        with self._lock:
            self._subscribers.discard(entry)

    async def subscribe(self) -> AsyncIterator[ServerEvent]:
        entry, _ = self._register()
        try:
            while True:
                yield await entry[1].get()
        finally:
            self._unregister(entry)


def format_sse(event: ServerEvent, boot: str) -> str:
    data = json.dumps(event.data, separators=(",", ":"), ensure_ascii=False)
    return f"id: {boot}-{event.id}\nevent: {event.type}\ndata: {data}\n\n"


async def event_stream(
    broker: EventBroker, last_event_id: str | None, *, heartbeat_s: float = 15.0
) -> AsyncIterator[str]:
    """Replay what the client missed, then stream new events, with a keep-alive comment while idle."""
    entry, position = broker._register()  # register before replaying so nothing published in between is lost
    try:
        resumed = None if last_event_id is None else broker.resume(last_event_id)
        if resumed is not None:
            last_sent, missed = resumed
            for event in missed:
                last_sent = event.id
                yield format_sse(event, broker.boot)
        else:
            last_sent = position
            if last_event_id is None:
                # A bare id line: the browser records its position without receiving an event.
                yield f"id: {broker.boot}-{position}\n\n"
            else:
                yield format_sse(ServerEvent(position, "resync", {}), broker.boot)
        while True:
            try:
                event = await asyncio.wait_for(entry[1].get(), heartbeat_s)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if event.id > last_sent:
                last_sent = event.id
                yield format_sse(event, broker.boot)
    finally:
        broker._unregister(entry)
