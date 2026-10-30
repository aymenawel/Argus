"""A recipe and plan drafted from the researcher's words (D-73). Muse Spark answers within the toolbox; code checks the
answer's schema, builds a Recipe (the same checks as a recipe file), and requires the plan's metric to be one the
recipe measures. A failed answer goes back once with its reasons; a second failure is refused with them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from argus.claims.schema import schema_errors
from argus.domain import Direction, ModelCallDraft, PlanDraft
from argus.reason import Reasoner, ReasonError, ReasonTask
from argus.reason.prompts import load_prompt, prompt_version
from argus.recipes.model import Concept, Recipe
from argus.recipes.toolbox import BY_METHOD, recipe_spec_schema, toolbox_text

SAFETY_WARNING = "Argus won't automate any hardware for this experiment. Take care: it mentions {what}."
# Word stems for flame, strong heat, pressure, hazardous chemicals and pathogens (CLAUDE.md rule 8); each matches its
# inflections ("burner", "pressurised", "bacterial"). A false alarm costs one warning line; a miss costs the warning.
HAZARDS = (
    r"flam\w*",
    r"fire\w*",
    r"candle\w*",
    r"burn\w*",
    r"bunsen",
    r"torch\w*",
    r"boil\w*",
    r"heat\w*",
    r"hot ?plates?",
    r"ovens?",
    r"stoves?",
    r"molten",
    r"solder\w*",
    r"pressur\w*",
    r"explo\w*",
    r"bottle rockets?",
    r"dry ice",
    r"liquid nitrogen",
    r"bleach\w*",
    r"acids?",
    r"ammonia",
    r"sodium hydroxide",
    r"caustic",
    r"lye",
    r"peroxide",
    r"chlorine",
    r"solvents?",
    r"acetone",
    r"mercury",
    r"bacteri\w*",
    r"pathogen\w*",
    r"e\. ?coli",
    r"salmonella",
    r"staph\w*",
    r"virus\w*",
    r"mou?ld\w*",
    r"swabs?",
    r"blood",
)
HAZARD = re.compile(r"\b(" + "|".join(HAZARDS) + r")(?!\w)", re.IGNORECASE)
FOOD_ACIDS = re.compile(r"\b(ascorbic|citric|acetic|lactic)\s+acids?\b", re.IGNORECASE)  # vitamin C, lemon, vinegar


class RecipeRefused(Exception):
    """Two answers failed the checks: the reasons, and every call made."""

    def __init__(self, reasons: list[str], calls: list[ModelCallDraft]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons
        self.calls = calls


@dataclass(frozen=True)
class RecipeDraft:
    recipe: Recipe
    plan: PlanDraft
    setup_hints: dict[str, Any]
    safety_notes: list[str] = field(default_factory=list)
    question: str = ""


def safety_screen(words: str, concepts: Sequence[str]) -> list[str]:
    """The fixed warning when the words or concepts mention flame, strong heat, pressure, hazardous chemicals or
    pathogens (food acids such as vitamin C or vinegar don't count)."""
    text = FOOD_ACIDS.sub(" ", " ".join([words, *concepts]))
    found = list(dict.fromkeys(m.group(1).lower() for m in HAZARD.finditer(text)))
    return [SAFETY_WARNING.format(what=", ".join(found))] if found else []


def _examples(templates: Mapping[str, Recipe]) -> str:
    """The template recipes in the answer's shape, so the model sees what a good recipe looks like."""
    shown = []
    for recipe in templates.values():
        measurements = [
            {"id": m.id, "method": m.method, "from": m.source, "touching": m.touching, "min_length_mm": m.min_length_mm}
            for m in recipe.measurements
            if m.method in BY_METHOD
        ]
        example = {
            "title": recipe.title,
            "concepts": [c.name for c in recipe.concepts],
            "measurements": measurements,
            "main_measurement": recipe.main_measurement,
            "analysis_step_s": recipe.analysis_step_s,
            "curve": recipe.curve,
            "rivals": recipe.rivals,
        }
        shown.append(json.dumps(example, ensure_ascii=False))
    return "EXAMPLES (recipes Argus already has)\n" + "\n".join(shown)


def _concept_problems(concepts: Any) -> list[str]:
    """The concept rules on the raw answer, so they are reported even when the rest has schema errors."""
    if not isinstance(concepts, list):
        return []
    problems = []
    for name in concepts:
        if not isinstance(name, str):
            continue
        try:
            Recipe.one_concept_each([Concept(name=name)])  # the same rule as recipe files
        except (ValueError, ValidationError) as error:
            problems.append(f"concepts: {error}")
    return problems


def _build(data: dict) -> tuple[Recipe, PlanDraft]:
    """The answer as a Recipe and a plan draft; raises ValueError with every reason."""
    measurements = []
    for m in data["measurements"]:
        tool = BY_METHOD[m["method"]]
        measurements.append(
            {
                "id": m["id"],
                "family": tool.family,
                "method": m["method"],
                "from": m["from"],
                "unit": tool.unit,
                "touching": m["touching"],
                "min_length_mm": m["min_length_mm"],
            }
        )
    try:
        recipe = Recipe.model_validate(
            {
                "id": "own",
                "version": 1,
                "title": data["title"],
                "default_mode": "smart_trigger",
                "analysis_step_s": data["analysis_step_s"],
                "curve": data["curve"],
                "rivals": data["rivals"],
                "concepts": [{"name": c} for c in data["concepts"]],
                "measurements": measurements,
                "main_measurement": data["main_measurement"],
            }
        )
    except ValidationError as error:
        raise ValueError([f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]) from error
    plan = data["plan"]
    if plan["metric"] not in recipe.stored_metrics():
        raise ValueError([f"plan.metric: '{plan['metric']}' is not one of {', '.join(recipe.stored_metrics())}"])
    draft = PlanDraft(
        hypothesis=plan["hypothesis"],
        prediction=plan["prediction"],
        threshold=plan["threshold"],
        rivals=list(data["rivals"]),
        metric=plan["metric"],
        direction=Direction(plan["direction"]),
        min_effect=max(0.0, float(plan["min_effect"])),
        checkpoint_s=max(0.0, float(plan["checkpoint_s"])),
        treatment=plan["treatment"] or None,
    )
    return recipe, draft


async def draft_recipe(
    words: str, *, reasoner: Reasoner, templates: Mapping[str, Recipe], experiment_id: str = "draft"
) -> tuple[RecipeDraft, list[ModelCallDraft]]:
    """A checked recipe and plan for the researcher's words, and every call made (to log)."""
    schema = recipe_spec_schema()
    version_of = templates.get("general") or next(iter(templates.values()))
    stable = (load_prompt("system/scientific-rules.md"), toolbox_text(), _examples(templates))
    calls: list[ModelCallDraft] = []
    reasons: list[str] = []
    for _ in range(2):
        task_text = load_prompt("setup/recipe.md")
        if reasons:
            task_text += "\n\nYour previous answer was rejected: " + "; ".join(reasons) + ". Fix exactly these."
        task = ReasonTask(
            function="recipe",
            experiment_id=experiment_id,
            prompt_version=prompt_version(version_of),
            stable=stable,
            variable=(f"RESEARCHER'S WORDS:\n{words}", task_text),
        )
        try:
            result = await reasoner(task, tier="routine", schema=schema, schema_name="ArgusRecipe")
        except ReasonError as error:
            calls.append(error.call)
            reasons = [str(error)]
            continue
        calls += [*result.failed_calls, result.call]
        data = result.data
        reasons = schema_errors(data, schema) + _concept_problems(
            data.get("concepts") if isinstance(data, dict) else None
        )
        if reasons:
            continue
        try:
            recipe, plan = _build(data)
        except ValueError as error:
            reasons = list(error.args[0]) if isinstance(error.args[0], list) else [str(error)]
            continue
        notes = list(data["safety_notes"]) + safety_screen(words, [c.name for c in recipe.concepts])
        return (
            RecipeDraft(recipe, plan, dict(data["setup_hints"]), notes, data["question_for_researcher"]),
            calls,
        )
    raise RecipeRefused(reasons, calls)
