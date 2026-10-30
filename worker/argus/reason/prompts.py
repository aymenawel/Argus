"""Prompt files from prompts/ and the assembly of a reasoning call's input (spec §7.1, prompts/README.md).

The order is cache-friendly: rules, method card and locked plan first (identical for a whole run), then the
MEASUREMENTS block, events, recent notes and the task. Prompt text lives in prompts/; this module only adds the
block headers and the data.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import cv2
import numpy as np

from argus.claims.refs import RefTable
from argus.config import REPO_ROOT
from argus.domain import Direction, Experiment, Note, Plan, RunEvent, VerdictLevel
from argus.reason import ReasonTask
from argus.recipes.model import Recipe

PROMPTS_DIR = REPO_ROOT / "prompts"
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
ALL_VERDICTS = tuple(level.value for level in VerdictLevel)
SNAPSHOT_QUALITY = 85


def load_prompt(relative: str) -> str:
    """A prompt file without its HTML comments (they are notes for people, not for the model)."""
    return COMMENT.sub("", (PROMPTS_DIR / relative).read_text(encoding="utf-8")).strip()


def _without_comments(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _without_comments(v) for k, v in node.items() if k != "$comment"}
    if isinstance(node, list):
        return [_without_comments(v) for v in node]
    return node


def load_schema(name: str) -> dict:
    return _without_comments(json.loads((PROMPTS_DIR / "schemas" / f"{name}.json").read_text(encoding="utf-8")))


def method_card(recipe: Recipe) -> str:
    """The recipe's method card, relative to prompts/: the general one for a recipe that has none of its own."""
    own = f"recipes/{recipe.id}/method.md"
    return own if (PROMPTS_DIR / own).is_file() else "recipes/general/method.md"


def prompt_version(recipe: Recipe) -> str:
    """Changes whenever a prompt, the recipe's method card or a schema changes, so the cache key does too."""
    digest = hashlib.sha256()
    files = [PROMPTS_DIR / method_card(recipe)]
    files += sorted(
        p for p in PROMPTS_DIR.rglob("*") if p.is_file() and "recipes" not in p.relative_to(PROMPTS_DIR).parts
    )
    for path in files:
        digest.update(path.relative_to(PROMPTS_DIR).as_posix().encode())
        digest.update(path.read_bytes())
    return "p" + digest.hexdigest()[:10]


def plan_block(plan: Plan | None) -> str:
    if plan is None or plan.locked_at is None:
        return "NO LOCKED PLAN"
    lines = [
        f"LOCKED PLAN (version {plan.version}, locked {plan.locked_at.isoformat()})",
        f"Hypothesis: {plan.hypothesis}",
        f"Prediction: {plan.prediction}",
        f"Success threshold: {plan.threshold}",
    ]
    if plan.metric and plan.direction:
        who = f"treatment vessels with condition '{plan.treatment}'" if plan.treatment else "every treatment vessel"
        if plan.quantity == "half_time":  # D-78: judged on the fitted curve, not the readings
            when = "sooner" if plan.direction is Direction.LOWER else "later"
            line = (
                f"Structured prediction: {who} reaches half its fitted plateau of {plan.metric} {when} than the "
                f"controls (a {plan.direction.value} half-way time)"
            )
        elif plan.quantity == "rate":
            line = (
                f"Structured prediction: {who} has a {plan.direction.value} fitted rate of {plan.metric} than the "
                "controls"
            )
        else:
            line = f"Structured prediction: {who} reads {plan.direction.value} than the controls on {plan.metric}"
        if plan.min_effect is not None:
            line += " by at least {ref:plan:min_effect}"
        if plan.checkpoint_s is not None:
            line += ", judged from {ref:plan:checkpoint} of run time on"
        lines.append(line + ".")
    lines.append("Rival explanations: " + ("; ".join(plan.rivals) if plan.rivals else "none listed"))
    return "\n".join(lines)


def measurements_block(refs: RefTable) -> str:
    lines = ["MEASUREMENTS (cite only as {ref:<id>})"]
    lines += [f"{r.id} | {r.label} | {r.display}" for r in (refs.get(i) for i in refs.ids()) if r is not None]
    return "\n".join(lines)


def events_block(events: Sequence[RunEvent], refs: RefTable, labels: Mapping[str, str] | None = None) -> str:
    """Events by id, each timed by its ref (never as a written number the model could copy)."""
    labels = labels or {}
    by_event = {
        e: r.id for r in (refs.get(i) for i in refs.ids()) if r is not None and r.kind == "event" for e in r.evidence
    }
    lines = ["EVENTS (id | kind | vessel | when)"]
    for event in events:
        when = f"{{ref:{by_event[event.id]}}}" if event.id in by_event else "time not in MEASUREMENTS"
        what = event.detail.get("message") or event.detail.get("rule") or ""
        vessel = labels.get(event.vessel_id, "all vessels") if event.vessel_id else "all vessels"
        lines.append(f"{event.id} | {event.kind}{f' ({what})' if what else ''} | {vessel} | {when}")
    return "\n".join(lines) if len(lines) > 1 else "EVENTS: none"


def notes_block(notes: Sequence[Note]) -> str:
    """The last three notes' observations, with their numbers masked: context, never a source of numbers."""
    recent = [n for n in notes if n.body.get("observation")][-3:]
    if not recent:
        return "RECENT NOTES: none"
    lines = ["RECENT NOTES (numbers masked as [n]; cite current values only from MEASUREMENTS)"]
    lines += [f"- {NUMBER.sub('[n]', str(n.body['observation']))}" for n in recent]
    return "\n".join(lines)


def _stable(recipe: Recipe, plan: Plan | None) -> tuple[str, ...]:
    return (
        load_prompt("system/scientific-rules.md"),
        load_prompt(method_card(recipe)),
        plan_block(plan),
    )


def note_task(
    level: str,
    recipe: Recipe,
    plan: Plan | None,
    refs: RefTable,
    events: Sequence[RunEvent],
    notes: Sequence[Note],
    *,
    rejected: Sequence[str] = (),
    allowed: Sequence[str] = ALL_VERDICTS,
    experiment_id: str | None = None,
    labels: Mapping[str, str] | None = None,
) -> ReasonTask:
    task = load_prompt("routine/note.md").replace("<<LEVEL>>", level)
    if rejected:
        task += "\n\nYour previous answer was rejected: " + "; ".join(rejected) + ". Fix exactly these."
    return ReasonTask(
        function="note",
        experiment_id=experiment_id or (plan.experiment_id if plan else "none"),
        prompt_version=prompt_version(recipe),
        stable=_stable(recipe, plan),
        variable=(
            measurements_block(refs),
            events_block(events, refs, labels),
            notes_block(notes),
            "ALLOWED VERDICTS NOW: " + ", ".join(allowed),
            task,
        ),
    )


def verdict_task(
    recipe: Recipe,
    plan: Plan | None,
    refs: RefTable,
    *,
    checks: Sequence[str],
    allowed: Sequence[str],
    events: Sequence[RunEvent],
    notes: Sequence[Note],
    experiment_id: str | None = None,
    labels: Mapping[str, str] | None = None,
    rejected: Sequence[str] = (),
) -> ReasonTask:
    task = load_prompt("deep/verdict.md")
    if rejected:
        task += "\n\nYour previous answer was rejected: " + "; ".join(rejected) + ". Fix exactly these."
    return ReasonTask(
        function="verdict_draft",
        experiment_id=experiment_id or (plan.experiment_id if plan else "none"),
        prompt_version=prompt_version(recipe),
        stable=_stable(recipe, plan),
        variable=(
            measurements_block(refs),
            events_block(events, refs, labels),
            notes_block(notes),
            "CHECKS (computed in code)\n" + "\n".join(f"- {c}" for c in checks),
            "ALLOWED VERDICTS: " + ", ".join(allowed),
            task,
        ),
    )


def critique_task(
    recipe: Recipe,
    plan: Plan | None,
    refs: RefTable,
    *,
    checks: Sequence[str],
    allowed: Sequence[str],
    draft: dict,
    events: Sequence[RunEvent] = (),
    experiment_id: str | None = None,
    labels: Mapping[str, str] | None = None,
) -> ReasonTask:
    """The critique sees what the draft saw (measurements, events, checks), so it judges the draft's claims
    against the same evidence."""
    return ReasonTask(
        function="verdict_critique",
        experiment_id=experiment_id or (plan.experiment_id if plan else "none"),
        prompt_version=prompt_version(recipe),
        stable=_stable(recipe, plan),
        variable=(
            measurements_block(refs),
            events_block(events, refs, labels),
            "CHECKS (computed in code)\n" + "\n".join(f"- {c}" for c in checks),
            "ALLOWED VERDICTS: " + ", ".join(allowed),
            "DRAFT VERDICT\n" + json.dumps(draft, ensure_ascii=False, indent=1),
            load_prompt("deep/verdict-critique.md"),
        ),
    )


def next_run_task(
    recipe: Recipe,
    plan: Plan | None,
    refs: RefTable,
    *,
    numbers: Sequence[tuple[str, str]],
    verdict: str,
    checks: Sequence[str],
    open_rivals: Sequence[str],
    experiment_id: str,
    rejected: Sequence[str] = (),
) -> ReasonTask:
    """The next-run suggestion's task (D-80): code's numbers as (ref id or name, reason) pairs, the reasons' and the
    verdict checks' digits masked so the only numbers the model can cite are the refs."""
    task = load_prompt("deep/next-run.md")
    if rejected:
        task += "\n\nYour previous answer was rejected: " + "; ".join(rejected) + ". Fix exactly these."
    return ReasonTask(
        function="next_run",
        experiment_id=experiment_id,
        prompt_version=prompt_version(recipe),
        stable=_stable(recipe, plan),
        variable=(
            measurements_block(refs),
            f"VERDICT: {verdict}\nCHECKS (computed in code; numbers masked as [n])\n"
            + "\n".join(f"- {NUMBER.sub('[n]', c)}" for c in checks),
            "OPEN RIVALS: " + ("; ".join(open_rivals) if open_rivals else "none"),
            "NEXT-RUN NUMBERS (computed in code; cite as {ref:<id>}, reasons with numbers masked as [n])\n"
            + "\n".join(f"- {name}: {NUMBER.sub('[n]', reason)}" for name, reason in numbers),
            task,
        ),
    )


def describe_task(experiment: Experiment, recipe: Recipe, words: str) -> tuple[ReasonTask, dict]:
    """The setup draft's task, and its schema with the recipe's metrics filled into the `metric` enum."""
    schema = load_schema("recipe_draft")
    metrics = recipe.stored_metrics()
    schema["properties"]["metric"]["enum"] = metrics
    units = {m.id: m.unit for m in recipe.measurements}
    listed = ", ".join(f"{name} ({units.get(name, units.get(name.rsplit('_', 1)[0], ''))})" for name in metrics)
    task = ReasonTask(
        function="describe",
        experiment_id=experiment.id,
        prompt_version=prompt_version(recipe),
        stable=(load_prompt("system/scientific-rules.md"), load_prompt(method_card(recipe))),
        variable=(
            f"RECIPE: {recipe.title}\nMEASURABLE METRICS: {listed}\nRECIPE RIVALS: {'; '.join(recipe.rivals)}",
            load_prompt("setup/describe.md"),
            f"RESEARCHER'S WORDS:\n{words}",
        ),
    )
    return task, schema


def snapshot_jpeg(image_bgr: np.ndarray, px: int = 768) -> bytes:
    """A frame for a reasoning call: JPEG, at most `px` on the long side (KB 04: about 1,700 tokens per two)."""
    height, width = image_bgr.shape[:2]
    scale = px / max(height, width)
    if scale < 1:
        image_bgr = cv2.resize(image_bgr, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_QUALITY])
    if not ok:
        raise ValueError("could not encode the snapshot")
    return encoded.tobytes()
