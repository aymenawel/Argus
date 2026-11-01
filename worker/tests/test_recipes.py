import json

import pytest

from argus.config import REPO_ROOT
from argus.recipes.loader import RecipeError, load_all, load_recipe

VALID = {
    "id": "x",
    "version": 1,
    "title": "Test recipe",
    "default_mode": "continuous",
    "analysis_step_s": 5.0,
    "main_measurement": "root_length",
    "curve": "logistic",
    "rivals": ["light"],
    "default_views": ["curves"],
    "concepts": [{"name": "root"}],
    "measurements": [
        {"id": "root_length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"}
    ],
    "events": [],
}


def _toml_value(value):
    return json.dumps(value)  # strings, numbers, bools and lists of them read the same in TOML


def write_recipe(directory, data):
    """Write the flat recipe shape used here as TOML: top-level keys first, then arrays of tables."""
    tables = {k: v for k, v in data.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
    lines = [f"{k} = {_toml_value(v)}" for k, v in data.items() if k not in tables and v != []]
    for name, rows in tables.items():
        for row in rows:
            lines += [f"[[{name}]]", *(f"{k} = {_toml_value(v)}" for k, v in row.items())]
    path = directory / f"{data['id']}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_bundled_recipes_load_and_point_to_real_measurements():
    recipes = load_all(REPO_ROOT / "recipes")
    assert set(recipes) == {"seed-germination", "colour-reaction", "foam-height", "general", "colony-spread"}
    for r in recipes.values():
        assert r.main_measurement in {m.id for m in r.measurements}


def test_only_foam_can_vanish_and_metrics_map_back_to_their_concepts():
    """Foam can really collapse to nothing; a colony or a root SAM stops finding is a miss (D-90)."""
    recipes = load_all(REPO_ROOT / "recipes")
    assert [c.can_vanish for c in recipes["foam-height"].concepts] == [True]
    assert not any(c.can_vanish for r in recipes.values() if r.id != "foam-height" for c in r.concepts)
    general = recipes["general"]
    lab = next(m for m in general.measurements if m.method == "lab_mean")
    assert general.measurement_for(f"{lab.id}_a") is lab
    assert recipes["seed-germination"].measurement_for("root_length").source == "root"
    with pytest.raises(KeyError):
        general.measurement_for("nope")


def test_image_sequences_show_sam_the_whole_frame_unless_a_recipe_asks_for_one_vessel_at_a_time():
    """Small seeds stand out on the whole plate; a faint colony filling its dish is only found in the dish (D-89)."""
    recipes = load_all(REPO_ROOT / "recipes")
    assert {r.id: r.stills_view for r in recipes.values()} == {
        "seed-germination": "frame",
        "colour-reaction": "frame",
        "foam-height": "frame",
        "general": "frame",
        "colony-spread": "vessel",
    }
    assert [c.name for c in recipes["colony-spread"].concepts] == ["microbial colony"]


@pytest.mark.parametrize(
    "patch,field",
    [
        ({"concepts": [{"name": "seed, root"}]}, "concepts"),
        (
            {"measurements": [{"id": "x", "family": "size", "method": "delta_e", "from": "root", "unit": "mm"}]},
            "method",
        ),
        ({"main_measurement": "nope"}, "main_measurement"),
    ],
)
def test_invalid_recipes_are_rejected_with_file_and_field(tmp_path, patch, field):
    path = write_recipe(tmp_path, {**VALID, **patch})
    with pytest.raises(RecipeError, match=rf"{path.name}: {field}"):
        load_recipe(path)
