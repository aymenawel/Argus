"""Load recipes from TOML files and report problems as '<file>: <field>: <problem>'."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from argus.recipes.model import Recipe


class RecipeError(ValueError):
    pass


def _field(loc: tuple) -> str:
    names = [part for part in loc if isinstance(part, str)]
    return names[-1] if names else "recipe"


def load_recipe(path: Path) -> Recipe:
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise RecipeError(f"{path.name}: toml: {error}") from error
    try:
        recipe = Recipe.model_validate(data)
    except ValidationError as error:
        first = error.errors()[0]
        raise RecipeError(f"{path.name}: {_field(first['loc'])}: {first['msg']}") from error
    if recipe.id != path.stem:
        raise RecipeError(f"{path.name}: id: '{recipe.id}' must match the file name")
    return recipe


def load_all(recipes_dir: Path) -> dict[str, Recipe]:
    return {recipe.id: recipe for recipe in (load_recipe(p) for p in sorted(Path(recipes_dir).glob("*.toml")))}
