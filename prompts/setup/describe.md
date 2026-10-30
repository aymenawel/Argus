<!--
Purpose: draft an experiment's plan from the researcher's own words (Muse Spark, setup wizard). Output:
prompts/schemas/recipe_draft.json, with the recipe's measurement ids filled into the `metric` enum. Nothing is
saved: the researcher edits every field. The numbers here are the researcher's intended values, not measurements.
-->

# Task: draft a plan for this experiment

The researcher described what they want to test (RESEARCHER'S WORDS). The experiment uses the recipe above; stay within its measurements.

- `hypothesis`: one testable sentence.
- `prediction`: what the treatment vessels should show against the controls, measurable with the recipe's metric.
- `threshold`: the success threshold in words.
- `metric`: the recipe measurement that tests the prediction. `direction`: `higher` or `lower` (treatment relative to control).
- `quantity`: what the prediction compares. `half_time` when it is about speed (faster, sooner, slower: the fitted time to half the final value; `direction` `lower` means faster, `min_effect` in hours); `rate` when it is about a growth or reaction rate (`min_effect` in the metric's unit per hour); `level` when it is about how much by a time.
- `min_effect`: the smallest difference that would matter, in the metric's unit; use the researcher's number if they gave one, else a modest value you can justify.
- `checkpoint_s`: the run time in seconds from which a verdict makes sense.
- `treatment`: the condition value the prediction is about, or an empty string for every treatment vessel.
- `factor` and `factor_unit`: what differs between vessels (for example water temperature, °C).
- `conditions`: one entry per vessel group the researcher mentioned, with `role` control or treatment. Suggest at least two vessels per group.
- `rivals`: the recipe's rival explanations that apply, plus any the description suggests.
- `question_for_researcher`: one question if something essential is missing, else empty.

Never propose automatic hardware actions or anything involving flame, strong heat, pressure, hazardous chemicals or pathogens; give no medical advice.
