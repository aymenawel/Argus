"""Ask Argus (D-97): questions about the moment on screen, answered from the run's own records."""

import sqlite3

import pytest

from argus.config import REPO_ROOT, load_settings
from argus.domain import ChatMessageDraft, RunMode, RunSource, SourceKind
from argus.pipeline.chat import ChatRefused, ask_chat
from argus.reason import ReasonError
from argus.recipes.loader import load_all
from argus.storage import repos
from tests.api_client import logged_functions
from tests.reasoning import FakeReasoner, call
from tests.records import finished_run

COLOUR = load_all(REPO_ROOT / "recipes")["colour-reaction"]
FREE = {"answer": "Glass B is about twelve units darker.", "refs_used": []}


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


def settings_for(tmp_path, **env):
    return load_settings({"ARGUS_DATA_DIR": str(tmp_path), **env})


async def ask(db, tmp_path, reasoner, *, run=None, t=6600.0, question="What's happening now?", **env):
    run = run or finished_run(db, tmp_path)
    return await ask_chat(db, settings_for(tmp_path, **env), run, COLOUR, reasoner, t, question)


@pytest.mark.anyio
async def test_a_clean_answer_is_rendered_chipped_and_stored(db, tmp_path):
    reasoner = FakeReasoner([{"answer": "Glass B changed by {ref:m:B:delta_e}.", "refs_used": ["m:B:delta_e"]}])
    message = await ask(db, tmp_path, reasoner)
    assert message.check_status == "passed" and "{ref:" not in message.answer and "ΔE" in message.answer
    assert message.body["chips"][0]["ref"] == "m:B:delta_e" and message.body["refs_used"] == ["m:B:delta_e"]
    assert logged_functions(db) == ["chat"] and message.model_call_id is not None
    assert len(reasoner.images[0]) == 1  # the picture at that moment
    assert [m.id for m in repos.chat_for_run(db, message.run_id)] == [message.id]


@pytest.mark.anyio
async def test_a_free_number_is_retried_then_written_by_code(db, tmp_path):
    reasoner = FakeReasoner([FREE, FREE])
    message = await ask(db, tmp_path, reasoner)
    assert reasoner.calls == 2 and message.check_status == "fallback"
    assert message.answer.startswith("I couldn't answer that without guessing a number.")
    assert "Sample A" in message.answer and "twelve" not in message.answer
    assert "rejected" in reasoner.tasks[1].variable[-2]  # the second try is told why


@pytest.mark.anyio
async def test_a_model_error_gives_the_code_written_answer(db, tmp_path):
    failed = ReasonError("timed out", call("chat", status="error", error="timeout"))
    message = await ask(db, tmp_path, FakeReasoner([failed, failed]))
    assert message.check_status == "fallback" and logged_functions(db) == ["chat", "chat"]


@pytest.mark.anyio
async def test_the_moment_is_clamped_to_the_run(db, tmp_path):
    reasoner = FakeReasoner([{"answer": "Glass B is darker.", "refs_used": []}])
    message = await ask(db, tmp_path, reasoner, t=1e9)
    assert message.t == 6600.0  # the last picture
    assert "MOMENT ASKED ABOUT: 1:50" in reasoner.tasks[0].variable


@pytest.mark.anyio
async def test_an_answer_starting_with_its_field_name_reads_without_it(db, tmp_path):
    message = await ask(db, tmp_path, FakeReasoner([{"answer": "Answer: the glass is clear.", "refs_used": []}]))
    assert message.answer == "The glass is clear."


@pytest.mark.anyio
async def test_a_run_with_nothing_measured_yet(db, tmp_path):
    run = finished_run(db, tmp_path, frames=1, readings=False)
    message = await ask(db, tmp_path, FakeReasoner([FREE, FREE]), run=run, t=0.0)
    assert message.answer == "Argus hasn't measured anything yet at this moment."
    experiment = repos.create_experiment(db, "Nothing yet", "colour-reaction", 1)
    empty = repos.create_run(db, experiment.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    reasoner = FakeReasoner([{"answer": "Nothing has happened yet.", "refs_used": []}])
    message = await ask(db, tmp_path, reasoner, run=empty, t=30.0)
    assert message.t == 0.0 and reasoner.images[0] == ()  # no picture yet, none sent


@pytest.mark.anyio
async def test_the_spending_limit_refuses_before_any_call(db, tmp_path):
    reasoner = FakeReasoner([])
    with pytest.raises(ChatRefused, match="spending limit"):
        await ask(db, tmp_path, reasoner, RUN_SPEND_CAP_USD="0.005")
    assert reasoner.calls == 0


@pytest.mark.anyio
async def test_the_last_six_messages_are_the_history(db, tmp_path):
    run = finished_run(db, tmp_path)
    for letter in "abcdefg":
        repos.add_chat_message(db, run.id, message(60.0, f"Question {letter}?"))
    reasoner = FakeReasoner([{"answer": "Glass B is darker.", "refs_used": []}])
    await ask(db, tmp_path, reasoner, run=run)
    history = next(part for part in reasoner.tasks[0].variable if part.startswith("CONVERSATION SO FAR"))
    assert "Question a?" not in history and "Question b?" in history and "Question g?" in history
