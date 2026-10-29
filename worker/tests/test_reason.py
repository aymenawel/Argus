"""reason() against a recorded Muse Spark response (tests/fixtures/reason, made by probes/record_reason.py) and a
fake client. No network."""

import ast
import copy
import json
from pathlib import Path

import pytest
from openai._models import construct_type
from openai.types.responses import Response
from pydantic import SecretStr

from argus.config import Settings
from argus.reason import ReasonError, ReasonTask, SettingsReasoner, reason

FIXTURES = Path(__file__).parent / "fixtures" / "reason"
ARGUS = Path(__file__).parents[1] / "argus"
SETTINGS = Settings(model_api_key=SecretStr("test-key"))
NOTE_SCHEMA = {"type": "object", "additionalProperties": False, "required": [], "properties": {}}
TASK = ReasonTask(
    function="note",
    experiment_id="exp_1",
    prompt_version="v1",
    stable=("# Argus scientific rules", "method card", "LOCKED PLAN"),
    variable=("MEASUREMENTS (cite only as {ref:<id>})", "Write one checkpoint note."),
)
JPEG = b"\xff\xd8 fake jpeg"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class FakeResponses:
    def __init__(self, answers):
        self.answers, self.requests = list(answers), []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        # Built the way the SDK builds real responses: leniently (Meta's shape doesn't pass strict validation).
        return construct_type(type_=Response, value=answer)


class FakeClient:
    def __init__(self, *answers):
        self.responses = FakeResponses(answers)

    @property
    def requests(self):
        return self.responses.requests


def expected_cost(response: dict, prices: tuple[float, float, float]) -> float:
    usage = response["usage"]
    cached = usage["input_tokens_details"]["cached_tokens"] or 0
    fresh = usage["input_tokens"] - cached
    return (fresh * prices[0] + cached * prices[1] + usage["output_tokens"] * prices[2]) / 1e6


@pytest.mark.anyio
async def test_a_routine_call_sends_cache_key_effort_and_strict_schema():
    fake = FakeClient(fixture("note-response"))
    result = await reason(
        TASK, tier="routine", schema=NOTE_SCHEMA, schema_name="ArgusNote", images=[JPEG], settings=SETTINGS, client=fake
    )
    sent = fake.requests[0]
    assert sent["model"] == "muse-spark-1.3" and sent["prompt_cache_key"] == "argus:exp_1:routine:v1"
    assert sent["reasoning"] == {"effort": "minimal"} and sent["max_output_tokens"] == 4000
    assert sent["text"]["format"] == {"type": "json_schema", "name": "ArgusNote", "schema": NOTE_SCHEMA, "strict": True}
    content = sent["input"][0]["content"]
    assert [c["text"] for c in content[:5]] == [*TASK.stable, *TASK.variable]  # stable prefix first, for caching
    assert content[-1]["type"] == "input_image" and content[-1]["image_url"].startswith("data:image/jpeg;base64,")
    assert result.data["level"] == "checkpoint" and result.model == "muse-spark-1.3" and not result.fell_back
    call = result.call
    assert call.status == "ok" and call.function == "note" and call.tier == "routine" and call.images == 1
    assert (call.input_tokens, call.output_tokens, call.reasoning_tokens) == (591, 1307, 1041)
    assert call.cost_usd == pytest.approx(expected_cost(fixture("note-response"), (1.25, 0.15, 4.25)))
    assert call.cache_key == "argus:exp_1:routine:v1"


@pytest.mark.anyio
async def test_cached_tokens_are_billed_at_the_cached_price():
    answer = copy.deepcopy(fixture("note-response"))
    answer["usage"]["input_tokens_details"]["cached_tokens"] = 500
    result = await reason(
        TASK, tier="routine", schema=NOTE_SCHEMA, schema_name="ArgusNote", settings=SETTINGS, client=FakeClient(answer)
    )
    assert result.call.cached_tokens == 500
    assert result.call.cost_usd == pytest.approx(expected_cost(answer, (1.25, 0.15, 4.25)))


@pytest.mark.anyio
async def test_an_incomplete_answer_is_an_error_and_never_parsed():
    answer = fixture("note-response") | {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    with pytest.raises(ReasonError) as failure:
        await reason(
            TASK,
            tier="routine",
            schema=NOTE_SCHEMA,
            schema_name="ArgusNote",
            settings=SETTINGS,
            client=FakeClient(answer),
        )
    call = failure.value.call
    assert call.status == "error" and "max_output_tokens" in call.error and call.cost_usd > 0  # the tokens were billed


@pytest.mark.anyio
async def test_text_that_is_not_json_is_an_error():
    answer = copy.deepcopy(fixture("note-response"))
    answer["output"][-1]["content"][0]["text"] = '{"level": "checkpoint", "observ'
    with pytest.raises(ReasonError) as failure:
        await reason(
            TASK,
            tier="routine",
            schema=NOTE_SCHEMA,
            schema_name="ArgusNote",
            settings=SETTINGS,
            client=FakeClient(answer),
        )
    assert "JSON" in failure.value.call.error


@pytest.mark.anyio
async def test_a_transport_failure_is_an_error_with_no_cost():
    with pytest.raises(ReasonError) as failure:
        await reason(
            TASK,
            tier="routine",
            schema=NOTE_SCHEMA,
            schema_name="ArgusNote",
            settings=SETTINGS,
            client=FakeClient(RuntimeError("connection reset")),
        )
    assert failure.value.call.cost_usd == 0 and "connection reset" in failure.value.call.error


@pytest.mark.anyio
async def test_the_deep_tier_falls_back_to_spark_at_high_effort():
    fake = FakeClient(RuntimeError("wonder unavailable"), fixture("note-response"))
    result = await reason(
        TASK, tier="deep", schema=NOTE_SCHEMA, schema_name="ArgusNote", settings=SETTINGS, client=fake
    )
    assert [r["model"] for r in fake.requests] == ["muse-wonder-1.0", "muse-spark-1.3"]
    assert fake.requests[0]["reasoning"] == {"effort": "medium"} and fake.requests[0]["max_output_tokens"] == 8000
    assert fake.requests[1]["reasoning"] == {"effort": "high"}
    assert result.fell_back and result.model == "muse-spark-1.3" and result.call.tier == "deep"
    assert [c.status for c in result.failed_calls] == ["error"] and result.failed_calls[0].model == "muse-wonder-1.0"


@pytest.mark.anyio
async def test_the_reasoner_keeps_one_client_and_closes_it():
    reasoner = SettingsReasoner(SETTINGS)
    client = reasoner.client
    assert reasoner.client is client and client.max_retries == 0 and client.timeout.read == 120.0
    await reasoner.aclose()
    assert client.is_closed()


def imports_of(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_only_the_two_model_modules_import_openai():
    importers = {p.relative_to(ARGUS).as_posix() for p in ARGUS.rglob("*.py") if "openai" in imports_of(p)}
    assert importers == {"segment/sam.py", "reason/client.py"}
