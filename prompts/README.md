# Prompts

All model prompts live here, never inline in code (decision D-07 in `docs/knowledge-base/15-decisions-log.md`).

| File | Sent with | Tier | Notes |
| --- | --- | --- | --- |
| `system/scientific-rules.md` | Every reasoning call, as the first, stable part of the input so prompt caching applies | routine + deep | Keep under ~450 tokens |
| `deep/verdict-critique.md` | Verdicts, next-run suggestions, final report | deep only | Output validated against a JSON schema |
| `recipes/<recipe>/method.md` (to create) | Calls for that recipe only | both | Short method card: what to measure, typical curve, recipe-specific rival explanations |

## Order of a reasoning call's input (cache-friendly)

1. `system/scientific-rules.md` (identical every call)
2. Recipe method card (identical for a whole run)
3. Locked experiment plan (identical for a whole run)
4. Running summary (changes slowly)
5. MEASUREMENTS block, recent events, new notes, 1 or 2 snapshots (changes every call)

Stable content first means Meta's automatic prompt caching can reuse the prefix (`usage.input_tokens_details.cached_tokens` shows hits). Cached input costs $0.15/M on Muse Spark 1.3 and $0.20/M on Muse Wonder instead of $1.25 and $4.00.

## Why not load the full skills at runtime

The 7 relevant skills total about 15,700 words (~21,000 tokens). Sending them on 3,000 calls would add about $78 on Muse Spark. Instead: rules here (~450 tokens), math as Python functions, and method cards per recipe. See `docs/knowledge-base/12-skills.md`.
