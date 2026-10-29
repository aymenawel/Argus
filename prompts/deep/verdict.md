<!--
Purpose: the verdict draft (Muse Wonder, effort medium). Sent after the MEASUREMENTS block, the ceiling's checks
and the allowed verdicts, which code computed (spec §7.3). Output: prompts/schemas/verdict.json, checked for refs
and free numbers before it is kept. A second Wonder pass critiques it (verdict-critique.md).
-->

# Task: draft the verdict on the locked plan

Code has already decided which verdicts the data allows (ALLOWED VERDICTS) and why (CHECKS). Your job is to explain, not to recompute.

- `verdict`: choose from ALLOWED VERDICTS. If you would choose something else, choose the most cautious allowed one and say why in the explanation.
- `explanation`: three to five sentences of plain prose for the researcher, with no headings or labels inside (no "Observation:", no "Hypothesis status:"): what the treatment vessels did against the controls at the same time, how that compares with the plan's smallest effect and the noise floor, and what limits the conclusion. Every number as a `{ref:<id>}` token, each cited once.
- `rivals`: each of the plan's rival explanations with `status` (`ruled_out`, `open` or `unclear`) and a one-sentence `reason` that rests on the checks or on cited refs.
- `what_would_change_it`: the one observation that would move the verdict.
- `confidence` and `confidence_reason`.
- `refs_used`: every ref id you cited. `evidence_ids`: event or frame ids you rely on, or empty.

Use the locked plan only; later edits do not count. Write no digits or quantity words outside tokens.
