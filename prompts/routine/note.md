<!--
Purpose: the task of a routine note (Muse Spark, effort minimal). Sent last, after the MEASUREMENTS block,
recent events and notes. <<LEVEL>> is replaced by the note's level. Output: prompts/schemas/note.json.
The claim checker rejects any digit or quantity word outside a {ref:<id>} token.
-->

# Task: write one <<LEVEL>> note

- **event** notes say what just happened (a hand or object at the samples, a set threshold crossed, the camera moving, a picture SAM couldn't outline) and what it may mean for the measurements around it.
- **checkpoint** notes summarize the run since the last note: each sample's change, test samples against the control at the same time, anything that limits trust in the numbers.

Write for someone with no lab training: short, plain sentences in everyday words (rule 12). Start each field with its sentence, never with the field's name ("Observation: …").

Every field is checked, `rival_explanations` and `question_for_researcher` included: write no digits at all, not even 1, 2 or 16, and no number words (zero, one, two, ten, half, twice). Name things instead of counting them ("the cold glass (A)", "the test samples", "no seed yet"), and cite a ref when a count matters. Numbers you see in events, rules or limits (an object limit, a run time) are context: never repeat them.

- `observation`: what was measured or seen, every number as a `{ref:<id>}` token. Cite the few numbers that matter most (at most five), each once: never repeat a time or a value you already gave.
- `interpretation`: what it may mean; say "consistent with", never "proves" or "caused".
- `hypothesis_status`: one of the verdict levels allowed now (listed above the task). Before the plan's check time it is TOO_EARLY.
- `confidence` and `confidence_reason`: the one thing that limits confidence most.
- `rival_explanations`: the plan's rivals that still matter, in words.
- `next_step`: one suggestion, worded as one ("Consider …"), with no label in front of it, or empty.
- `refs_used`: every ref id you cited. `evidence_ids`: frame or event ids from the EVENTS block, or empty.
- `question_for_researcher`: one specific question when something is unclear, else empty.

If nothing changed beyond the normal wobble, say so in one sentence.
