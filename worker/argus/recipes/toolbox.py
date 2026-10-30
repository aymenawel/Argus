"""Argus's measuring toolbox: every method a recipe may use, with its family and unit, described in words for the
model that drafts recipes (D-73). The answer schema is built from it, so a draft can only choose what Argus measures.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import get_args

from argus.reason.prompts import load_schema
from argus.recipes.model import Recipe


@dataclass(frozen=True)
class Tool:
    method: str
    family: str
    unit: str
    words: str


TOOLBOX: tuple[Tool, ...] = (
    Tool("area", "size", "mm2", "the area an object covers, seen from the camera"),
    Tool("height", "size", "mm", "how high an object reaches above its base (foam, dough, a plant)"),
    Tool("skeleton_length", "size", "mm", "the length along a thin object (a root, a shoot, a crack)"),
    Tool("component_count", "count", "count", "how many separate objects of the concept there are"),
    Tool(
        "touching_count",
        "count",
        "count",
        "how many objects of the concept touch another concept at least min_length_mm long "
        "(seeds with a root, crystals on a thread)",
    ),
    Tool("lab_mean", "colour", "Lab", "the object's mean colour as L*, a* and b*"),
    Tool("delta_e", "colour", "dE00", "how far the object's colour has moved from its first reading (CIEDE2000)"),
)
BY_METHOD = {tool.method: tool for tool in TOOLBOX}
CURVES = get_args(Recipe.model_fields["curve"].annotation)


def toolbox_text() -> str:
    """The toolbox in words, for the drafting prompt."""
    lines = ["TOOLBOX (the only measurements Argus can make)"]
    lines += [f"- {t.method} ({t.unit}): {t.words}" for t in TOOLBOX]
    lines.append("CURVES: " + ", ".join(CURVES))
    return "\n".join(lines)


def recipe_spec_schema() -> dict:
    """The strict answer schema with the toolbox's methods and the recipe curves filled in."""
    schema = copy.deepcopy(load_schema("recipe_spec"))
    measurement = schema["properties"]["measurements"]["items"]["properties"]
    measurement["method"]["enum"] = [t.method for t in TOOLBOX]
    schema["properties"]["curve"]["enum"] = list(CURVES)
    return schema
