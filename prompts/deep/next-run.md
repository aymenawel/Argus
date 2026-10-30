<!--
Purpose: the next-run suggestion (Muse Wonder, D-80). Sent after MEASUREMENTS (with the next:* refs code computed),
the verdict and its checks, and the next-run numbers with code's reasons. Output: prompts/schemas/next_run.json,
checked for refs and free numbers like a note before it is kept; two failures and code writes the suggestion.
-->

# Task: explain the next run

Code has already computed the next run's numbers (NEXT-RUN NUMBERS): the vessels per condition (`next:replicates`), the run length (`next:hours`) and, for a numeric factor, the levels to try (`next:level:*`). Your job is to explain them and say what to change, not to recompute them or add others.

- `why`: two to four sentences of plain prose about the next run's numbers: why they follow from this run's spread, its curves and the plan's smallest effect. Don't retell the verdict; the researcher has it beside this. Cite each number as a `{ref:<id>}` token. When a number is unknown, say what the next run must give for it to be known.
- `change`: one or two sentences on what to do differently next time, resting on the verdict's checks and the open rivals (for example, put the conditions side by side in one run when run-to-run differences are open). Changes are for the researcher to make by hand: never suggest automatic hardware actions.
- `watch_for`: one if-this-then-that for the researcher to watch during the next run.
- `refs_used`: every ref id you cited.

Each field is plain prose with no headings or labels inside (no "Observation:", no "Suggestion:", no "Hypothesis status:"). A token renders with its unit ("{ref:next:replicates}" reads as a number of vessels), so don't repeat the unit after it.

Argus suggests; it never starts a run or moves hardware. Write no digits or quantity words outside tokens.
