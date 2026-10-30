"""The recipe an experiment uses: its own version (drafted from words, D-73) or a file template."""

from __future__ import annotations

from collections.abc import Mapping

from argus.domain import Experiment
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import own_recipe

OWN = "own"


def recipe_for(db: Database, templates: Mapping[str, Recipe], experiment: Experiment) -> Recipe:
    if experiment.recipe_id == OWN:
        recipe = own_recipe(db, experiment.id, experiment.recipe_version)
        if recipe is None:
            raise LookupError(f"experiment {experiment.id} has no own recipe version {experiment.recipe_version}")
        return recipe
    return templates[experiment.recipe_id]
