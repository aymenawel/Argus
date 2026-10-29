"""A scripted stand-in for reason() and builders of model answers, shared by the note and verdict tests."""

from __future__ import annotations

from argus.domain import ModelCallDraft
from argus.reason import ReasonError, ReasonResult, ReasonTask


def call(
    function: str = "note",
    *,
    status: str = "ok",
    cost: float = 0.005,
    model: str = "muse-spark-1.3",
    tier: str = "routine",
    error: str | None = None,
) -> ModelCallDraft:
    return ModelCallDraft(
        function=function,
        model=model,
        tier=tier,
        input_tokens=1000,
        output_tokens=300,
        cost_usd=cost,
        latency_s=1.0,
        status=status,
        error=error,
    )


class FakeReasoner:
    """Answers in order: a dict becomes a result, a ReasonError is raised, a ReasonResult is returned as it is."""

    def __init__(self, answers=()):
        self.answers, self.tasks = list(answers), []

    @property
    def calls(self) -> int:
        return len(self.tasks)

    async def __call__(self, task: ReasonTask, *, tier, schema, schema_name, images=()):
        self.tasks.append(task)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            if isinstance(answer, ReasonError):
                raise ReasonError(str(answer), answer.call.model_copy(update={"function": task.function, "tier": tier}))
            raise answer
        if isinstance(answer, ReasonResult):
            return answer
        model = "muse-wonder-1.0" if tier == "deep" else "muse-spark-1.3"
        return ReasonResult(answer, call(task.function, model=model, tier=tier), model, fell_back=False)


def clean_note(**overrides) -> dict:
    note = {
        "level": "checkpoint",
        "observation": "No change.",
        "interpretation": "",
        "hypothesis_status": "TOO_EARLY",
        "confidence": "low",
        "confidence_reason": "",
        "rival_explanations": [],
        "next_step": "",
        "refs_used": [],
        "evidence_ids": [],
        "question_for_researcher": "",
    }
    return note | overrides


def verdict_draft(
    verdict: str = "SUPPORTED", explanation: str = "C rose above the controls by {ref:diff:C:delta_e}.", **overrides
) -> dict:
    draft = {
        "verdict": verdict,
        "explanation": explanation,
        "rivals": [{"name": "lighting change", "status": "ruled_out", "reason": "Colour was corrected throughout."}],
        "what_would_change_it": "The controls catching up by the end of the run.",
        "confidence": "medium",
        "confidence_reason": "Few vessels per condition.",
        "refs_used": ["diff:C:delta_e"],
        "evidence_ids": [],
    }
    return draft | overrides


def critique(revised: str = "INCONCLUSIVE", **overrides) -> dict:
    answer = {
        "revised_verdict": revised,
        "confidence": "low",
        "confidence_reason": "Few vessels.",
        "what_would_change_it": "More replicates.",
        "findings": [
            {
                "item": "unit_of_analysis",
                "problem": "Few vessels.",
                "consequence": "Chance is hard to rule out.",
                "fix": "Add replicates.",
            }
        ],
        "refs_used": [],
    }
    return answer | overrides
