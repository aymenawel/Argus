import asyncio
import threading

import pytest

from argus.api.events import EventBroker, ServerEvent, event_stream, format_sse


def test_format_sse_is_exact():
    assert format_sse(ServerEvent(7, "note", {"a": 1}), "b00t") == 'id: b00t-7\nevent: note\ndata: {"a":1}\n\n'


def test_since_returns_later_events_and_history_is_bounded():
    b = EventBroker(history=3)
    for i in range(5):
        b.publish("m", {"i": i})
    assert [e.id for e in b.since(0)] == [3, 4, 5] and [e.id for e in b.since(4)] == [5]


@pytest.mark.anyio
async def test_stream_replays_then_delivers_an_event_published_from_another_thread():
    b = EventBroker()
    b.publish("m", {"i": 1})
    stream = event_stream(b, last_event_id=f"{b.boot}-0", heartbeat_s=60)
    assert (await anext(stream)).startswith(f"id: {b.boot}-1\n")
    threading.Thread(target=b.publish, args=("m", {"i": 2})).start()
    assert (await asyncio.wait_for(anext(stream), 2)).startswith(f"id: {b.boot}-2\n")
    await stream.aclose()


@pytest.mark.anyio
async def test_a_new_client_is_told_its_position_without_an_event():
    # A bare id line sets the browser's Last-Event-ID, so after a restart it reconnects with an id and is
    # told to resync, even if no event reached it before.
    b = EventBroker()
    b.publish("m", {"i": 1})
    stream = event_stream(b, last_event_id=None, heartbeat_s=60)
    assert await asyncio.wait_for(anext(stream), 2) == f"id: {b.boot}-1\n\n"
    b.publish("m", {"i": 2})
    assert (await asyncio.wait_for(anext(stream), 2)).startswith(f"id: {b.boot}-2\nevent: m\n")
    await stream.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize("stale", ["earlier boot", "plain number"])
async def test_a_client_from_before_a_restart_is_told_to_resync(stale):
    old = EventBroker()
    for i in range(5):
        old.publish("m", {"i": i})
    fresh = EventBroker()  # the worker restarted: ids count from 1 again
    last_id = f"{old.boot}-5" if stale == "earlier boot" else "5"
    stream = event_stream(fresh, last_event_id=last_id, heartbeat_s=60)
    assert "event: resync\n" in await asyncio.wait_for(anext(stream), 2)
    fresh.publish("m", {"i": 1})
    assert (await asyncio.wait_for(anext(stream), 2)).startswith(f"id: {fresh.boot}-1\n")
    await stream.aclose()


@pytest.mark.anyio
async def test_a_client_that_missed_more_than_the_history_is_told_to_resync():
    b = EventBroker(history=3)
    for i in range(6):
        b.publish("m", {"i": i})
    stream = event_stream(b, last_event_id=f"{b.boot}-1", heartbeat_s=60)  # 2 and 3 are gone
    assert (await asyncio.wait_for(anext(stream), 2)).startswith(f"id: {b.boot}-6\nevent: resync\n")
    await stream.aclose()
