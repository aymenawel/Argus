-- Recipes drafted from the researcher's words (D-73): each experiment's own recipe, one row per version.
-- A version never changes once saved; the experiment points at the version in use (experiments.recipe_id = 'own').

CREATE TABLE experiment_recipes (
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    version INTEGER NOT NULL CHECK (version >= 1),
    body TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('drafted', 'edited')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (experiment_id, version)
);

CREATE TRIGGER experiment_recipes_no_update BEFORE UPDATE ON experiment_recipes
BEGIN
    SELECT RAISE(ABORT, 'recipe versions are evidence');
END;
CREATE TRIGGER experiment_recipes_no_delete BEFORE DELETE ON experiment_recipes
BEGIN
    SELECT RAISE(ABORT, 'recipe versions are evidence');
END;
