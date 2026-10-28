import asyncio
import threading

import pytest

from argus.api.events import EventBroker, ServerEvent, event_stream, format_sse


def test_format_sse_is_exact():
    assert format_sse(ServerEvent(7, "note", {"a": 1})) == 'id: 7\nevent: note\ndata: {"a":1}\n\n'


def test_since_returns_later_events_and_history_is_bounded():
    b = EventBroker(history=3)
    for i in range(5):
        b.publish("m", {"i": i})
    assert [e.id for e in b.since(0)] == [3, 4, 5] and [e.id for e in b.since(4)] == [5]


@pytest.mark.anyio
async def test_stream_replays_then_delivers_an_event_published_from_another_thread():
    b = EventBroker()
    b.publish("m", {"i": 1})
    stream = event_stream(b, last_event_id=0, heartbeat_s=60)
    assert (await anext(stream)).startswith("id: 1\n")
    threading.Thread(target=b.publish, args=("m", {"i": 2})).start()
    assert (await asyncio.wait_for(anext(stream), 2)).startswith("id: 2\n")
    await stream.aclose()
