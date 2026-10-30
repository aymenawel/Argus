<!--
Purpose: draft a whole recipe and plan from the researcher's own words (Muse Spark, new-experiment dialog, D-73).
Output: prompts/schemas/recipe_spec.json, method and curve enums filled from the toolbox. Code derives each
measurement's family and unit and validates the result as a Recipe; nothing is saved until the researcher accepts.
The numbers here are suggestions the researcher confirms, not measurements.
-->

# Task: set Argus up for this experiment

The researcher said what they will do (RESEARCHER'S WORDS). Draft how Argus should watch and measure it, using only the TOOLBOX above. The EXAMPLES show recipes for experiments Argus already knows.

- `title`: a short name for the experiment.
- `concepts`: 1–4 things a camera can see and SAM can outline, each a short noun phrase for one thing ("seed", "root", "foam", "apple slice"). Never two things in one concept, never an abstract idea ("growth", "the change"). The same concepts are found in every vessel: the conditions (a species, a temperature, a dose) are told apart by which vessel they are in, so never name a concept after a condition ("rye seed" and "millet seed" are both "seed").
- `measurements`: what to measure on those concepts, each from the TOOLBOX, with a snake_case `id`. `from` names one concept. Use `touching_count` to count objects that carry another (a seed with a root): set `touching` to the touched concept and `min_length_mm` to the smallest length that counts; leave both null for every other method.
- `main_measurement`: the measurement that best answers the researcher's question.
- `analysis_step_s`: how often to take a reading, matched to how fast the thing changes (seconds for a fast reaction, minutes for dough, half an hour or more for seeds).
- `curve`: the shape the main measurement should follow over time.
- `rivals`: other explanations that could produce the same result in this setup (light, temperature, position, handling).
- `plan`: the hypothesis, the prediction (treatment against control), the success threshold in words, the `metric` (a measurement id; for lab_mean add _l, _a or _b), the `direction` (treatment higher or lower), the smallest difference that matters in the metric's unit, the run time in seconds from which a verdict makes sense, and the `treatment` condition the prediction is about (empty for every treatment vessel).
- `setup_hints`: the factor that differs between vessels, its unit (or empty), and the conditions the researcher mentioned with a role each. Suggest at least two vessels per condition.
- `safety_notes`: anything the researcher should take care with, or an empty list.
- `question_for_researcher`: one question if something essential is missing, else empty.

Never propose automatic hardware actions or anything involving flame, strong heat, pressure, hazardous chemicals or pathogens; give no medical advice.
