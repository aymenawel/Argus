"""Ask Argus (D-97): questions about the moment on screen, answered from the run's own records."""

import sqlite3

import pytest

from argus.domain import ChatMessageDraft
from argus.storage import repos
from tests.records import finished_run


def message(t: float, question: str = "What's happening now?") -> ChatMessageDraft:
    return ChatMessageDraft(
        t=t,
        question=question,
        answer="Glass B is changing.",
        body={"answer": "Glass B is changing.", "refs_used": [], "chips": []},
        check_status="passed",
        model_call_id=None,
    )


def test_a_chat_message_is_stored_and_listed_oldest_first(db, tmp_path):
    run = finished_run(db, tmp_path)
    first = repos.add_chat_message(db, run.id, message(60.0, "First?"))
    second = repos.add_chat_message(db, run.id, message(30.0, "Second?"))
    assert first.id.startswith("chat_") and first.run_id == run.id
    assert [m.question for m in repos.chat_for_run(db, run.id)] == ["First?", "Second?"]  # in the order asked
    assert [m.id for m in repos.chat_for_run(db, run.id, limit=1)] == [second.id]


def test_chat_messages_are_evidence(db, tmp_path):
    run = finished_run(db, tmp_path)
    repos.add_chat_message(db, run.id, message(60.0))
    with pytest.raises(sqlite3.IntegrityError, match="chat messages are evidence"), db.write() as c:
        c.execute("UPDATE chat_messages SET answer='x'")
    with pytest.raises(sqlite3.IntegrityError, match="chat messages are evidence"), db.write() as c:
        c.execute("DELETE FROM chat_messages")
