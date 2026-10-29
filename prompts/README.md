# Prompts

All model prompts live here, never inline in code (decision D-07 in `docs/knowledge-base/15-decisions-log.md`).

| File | Sent with | Tier | Notes |
| --- | --- | --- | --- |
| `system/scientific-rules.md` | Every reasoning call, as the first, stable part of the input so prompt caching applies | routine + deep | Keep under ~450 tokens |
| `deep/verdict-critique.md` | Verdicts, next-run suggestions, final report | deep only | Output validated against a JSON schema |
| `recipes/<recipe>/method.md` | Calls for that recipe only | both | Short method card (under 250 words): what is measured, typical curve, what counts as a real change, recipe-specific rivals and their checks |
| `routine/note.md` | Event and checkpoint notes | routine | `<<LEVEL>>` is replaced by the note's level; output `schemas/note.json` (v2) |
| `deep/verdict.md` | The verdict draft | deep | Output `schemas/verdict.json`; code computed the allowed verdicts and the checks |
| `setup/describe.md` | The setup wizard's plan draft | routine | Output `schemas/recipe_draft.json` with the recipe's metrics filled into `metric` |

**Numbers.** Models cite numbers only as `{ref:<id>}` tokens from the call's MEASUREMENTS block; the claim checker rejects any digit or quantity word outside a token, and code renders the tokens (spec §7.2). Recent notes are shown with their numbers masked as `[n]`.

## Order of a reasoning call's input (cache-friendly)

1. `system/scientific-rules.md` (identical every call)
2. Recipe method card (identical for a whole run)
3. Locked experiment plan (identical for a whole run)
4. Running summary (changes slowly)
5. MEASUREMENTS block, recent events, new notes, 1 or 2 snapshots (changes every call)

Stable content first means Meta's automatic prompt caching can reuse the prefix (`usage.input_tokens_details.cached_tokens` shows hits). Cached input costs $0.15/M on Muse Spark 1.3 and $0.20/M on Muse Wonder instead of $1.25 and $4.00.

## Why not load the full skills at runtime

The 7 relevant skills total about 15,700 words (~21,000 tokens). Sending them on 3,000 calls would add about $78 on Muse Spark. Instead: rules here (~450 tokens), math as Python functions, and method cards per recipe. See `docs/knowledge-base/12-skills.md`.
