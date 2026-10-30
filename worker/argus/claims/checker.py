"""The claim checker and the renderer (spec §7.2, D-40, D-41).

A model's text may carry numbers only as {ref:<id>} tokens whose ids are in that call's MEASUREMENTS block. Any
digit or quantity word outside a token, any unknown ref or evidence id, and a status above the verdict ceiling
reject the answer before anything is saved. Code then renders the tokens as each ref's display text.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from typing import Any

from argus.claims.refs import RefTable
from argus.domain import VerdictLevel

TOKEN = re.compile(r"\{ref:([A-Za-z0-9_:.\-]+)\}")
# Model and product names carry digits that are not claims; they are taken out before the digit check.
MODEL_NAMES = ("Muse Wonder 1.0", "Muse Spark 1.3", "muse-wonder-1.0", "muse-spark-1.3", "SAM 3.1", "sam-3.1")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
VESSEL_REFS = ("m:", "chg:", "diff:")  # ref ids that carry a vessel's label: m:<label>:<metric>
COUNTING = (
    "two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    "eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|"
    "zero|dozen|quarter"
)
# Quantity words, with their plurals and inflections ("hundreds", "doubled", "halving"), "-fold" on a number word
# ("tenfold", not "unfolded"), and percentages. "One" stays allowed: "one glass" is not a measured claim.
NUMBER_WORD = re.compile(
    r"\b(?:(?:" + COUNTING + r")s?"
    r"|(?:" + COUNTING + r"|multi|many)-?fold"
    r"|twice|half(?![-\s]?way\b)|halv(?:e|ed|es|ing)"  # "half-way" names a time (KB 18), not an amount
    r"|doubl(?:e|ed|es|ing)|tripl(?:e|ed|es|ing)|quadrupl(?:e|ed|es|ing)"
    r"|per\s?cent)\b|%",
    re.IGNORECASE,
)


NOTE_FIELDS = (
    "level",
    "observation",
    "interpretation",
    "hypothesis_status",
    "confidence",
    "confidence_reason",
    "rival_explanations",
    "next_step",
    "refs_used",
    "evidence_ids",
    "question_for_researcher",
)
NOTE_TEXT = (
    "observation",
    "interpretation",
    "confidence_reason",
    "rival_explanations[*]",
    "next_step",
    "question_for_researcher",
)


def _texts(data: Any, path: str) -> list[str]:
    """The strings at a field path: "a", "a[*]" (each item of a list) or "a[*].b" (field b of each item)."""
    head, _, rest = path.partition(".")
    if head.endswith("[*]"):
        items = data.get(head[:-3]) if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        if not rest:
            return [i for i in items if isinstance(i, str)]
        return [t for item in items for t in _texts(item, rest)]
    value = data.get(head) if isinstance(data, dict) else None
    if rest:
        return _texts(value, rest)
    return [value] if isinstance(value, str) else []


def vessel_names(refs: RefTable) -> list[str]:
    """The vessels' labels ("pg1-2", "A1") the refs name: a reader takes them for names, not counts, so their digits
    are not claims. A label that is only digits ("3") stays checked: it reads like a number. Longest first."""
    labels = {i.split(":")[1] for i in refs.ids() if i.startswith(VESSEL_REFS) and i.count(":") >= 2}
    return sorted((label for label in labels if any(c.isalpha() for c in label)), key=len, reverse=True)


def check_text_fields(data: dict, fields: Sequence[str], refs: RefTable) -> list[str]:
    """Reasons a model's text fails, empty when it is clean: unknown refs, numbers or quantity words outside refs."""
    reasons: list[str] = []
    names = [re.compile(rf"(?<![\w-]){re.escape(label)}(?![\w-])") for label in vessel_names(refs)]
    for path in fields:
        for text in _texts(data, path):
            for ref_id in TOKEN.findall(text):
                if ref_id not in refs:
                    reasons.append(f"unknown ref: {ref_id}")
            bare = TOKEN.sub(" ", text)
            for name in MODEL_NAMES:
                bare = bare.replace(name, " ")
            for label in names:  # a whole vessel label only: "pg1-23" is not "pg1-2"
                bare = label.sub(" ", bare)
            for number in NUMBER.findall(bare):
                reasons.append(f"number outside a ref in {path}: '{number}'")
            for char in sorted({c for c in bare if c.isnumeric() and not c.isascii()}):  # ½, Ⅲ, other scripts' digits
                reasons.append(f"number outside a ref in {path}: '{char}'")
            for match in NUMBER_WORD.finditer(bare):
                reasons.append(f"quantity in words in {path}: '{match.group(0).lower()}'")
    return list(dict.fromkeys(reasons))


def check_note(
    data: dict, refs: RefTable, *, allowed: Collection[VerdictLevel], evidence: Collection[str]
) -> list[str]:
    """The spec §7.2 checks, in order: the schema's fields, refs and numbers, the ceiling, the evidence."""
    reasons = [f"missing field: {name}" for name in NOTE_FIELDS if name not in data]
    reasons += check_text_fields(data, NOTE_TEXT, refs)
    for ref_id in data.get("refs_used") or []:
        if ref_id not in refs:
            reasons.append(f"unknown ref: {ref_id}")
    status = data.get("hypothesis_status")
    if status is not None and status not in {str(a) for a in allowed}:
        reasons.append(f"status above the ceiling: {status}")
    for evidence_id in data.get("evidence_ids") or []:
        if evidence_id not in evidence:
            reasons.append(f"unknown evidence: {evidence_id}")
    return list(dict.fromkeys(reasons))


def render(text: str, refs: RefTable) -> str:
    """Each {ref:<id>} token as its ref's display text; an unknown token stays as it is, visibly."""

    def display(match: re.Match[str]) -> str:
        ref = refs.get(match.group(1))
        return ref.display if ref is not None else match.group(0)

    return TOKEN.sub(display, text)


def render_note(data: dict, refs: RefTable) -> dict:
    """A checked note's body as it is stored and shown: every text field rendered."""
    body = dict(data)
    for name in ("observation", "interpretation", "confidence_reason", "next_step", "question_for_researcher"):
        if isinstance(body.get(name), str):
            body[name] = render(body[name], refs)
    body["rival_explanations"] = [render(r, refs) for r in body.get("rival_explanations") or []]
    return body
