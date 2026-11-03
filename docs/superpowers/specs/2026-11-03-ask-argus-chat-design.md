# Ask Argus: a chat about the moment you're watching (design)

Approved in conversation with Aymen on Nov 3, 2026 (decision D-97). Deadline context: submission Nov 4, 9 PM ET; the calm redesign and one-product demo mode follow this as a separate step.

## Goal

A researcher can ask Argus questions in plain words while a run is live or while rewatching any run, and get a short, plain answer about the moment on screen, grounded in that run's own data. Every number in an answer is one Argus measured.

## What the researcher sees

- The Run screen's side column has two tabs: **Notes** (today's feed) and **Ask Argus**.
- Ask Argus shows the run's past questions and answers, oldest first, a text box, and three suggested questions while the conversation is empty: "What's happening now?", "Which sample is changing the most?", "Can Argus judge the idea yet?".
- Each answer is labelled with the run time it is about ("about 4:12") and shows the number chips notes show; tapping a chip moves the playhead to that chip's time.
- The moment asked about is the playhead: live, it follows the newest analysed picture (as the feed does today); rewatching, it is where the researcher paused or scrubbed.
- While an answer is being written the box shows "Argus is looking…" and the input is disabled; an error shows in plain words under the box with the question kept so it can be sent again.
- In demo mode (the public link, `NEXT_PUBLIC_ARGUS_REPLAY=1`) the tab shows the saved conversation read-only, labelled "Saved questions from the app", with the input replaced by "Ask your own questions in the app".

## Worker

### API

- `GET /api/runs/{run_id}/chat` → `list[ChatMessage]`, oldest first. 404 for an unknown run.
- `POST /api/runs/{run_id}/chat` with `{ "t": float ≥ 0, "question": str (1–500 chars, trimmed) }` → the new `ChatMessage` (201).
  - 404 unknown run; 503 when reasoning is off (no `MODEL_API_KEY`), same wording as the verdict; 409 "This run has reached its spending limit" when the cap would be passed.
  - `t` is clamped to the run's analysed span (0 to the last analysed frame's t); the stored `t` is the clamped one.

### Record (never edited)

`ChatMessage`: `id` (`chat_…`), `run_id`, `t`, `question`, `answer` (rendered text, numbers as their displays), `body` (JSON: the model's raw `answer` with ref tokens, `refs_used`, `chips` as notes build them), `check_status` (`passed` | `fallback`), `model_call_id` (nullable), `created_at`. Migration `012_chat.sql` creates `chat_messages` with an index on `(run_id, t)` and no-update / no-delete triggers, as the evidence tables have. The SSE broker publishes `chat` with the message for other open pages.

### Context for one answer (`pipeline/chat.py`)

Built at the clamped `t`, from stored records only:
- the refs table `build_refs(db, run, t, recipe, plan)`: every number the answer may cite;
- events up to `t` (`events_block`), the latest three notes up to `t` with numbers masked (as the note task does), the plan, the verdicts allowed at `t` (`allowed_now`), and the latest verdict's level and explanation when one exists at or before `t`;
- the last six questions and answers of this run, numbers masked;
- the picture: the newest frame at or before `t`, read from disk and shrunk with `snapshot_jpeg` (no picture when none exists).

The task's stable part is the scientific rules plus the recipe's method card (so prompt caching works); the variable part is the blocks above, then the question.

### Model call, checks and fallback

- `reasoner(task, tier="routine", schema=chat_answer, schema_name="ArgusChatAnswer", images=…)`; logged with function `chat` like every call (model, tier, tokens, cost, latency).
- Spend: reserve the expected cost (`EXPECTED_CHAT_USD = 0.01`) against `run_spend_cap_usd` before calling, as notes do; release it after.
- Schema `prompts/schemas/chat_answer.json`: `{ "answer": string, "refs_used": string[] }`, strict.
- Checks, in order: schema errors; then the claim checker's `check_text_fields(data, ["answer"], refs)` (unknown refs, digits or quantity words outside refs); then every ref in `refs_used` exists. One retry with the reasons listed (as notes retry); the attempt is logged either way.
- Twice rejected, or the call failed: a code-written answer (`check_status="fallback"`, no model words): "I couldn't answer that without guessing a number. Here is what Argus measured at {time}: Sample A (test, cold): colour change 3.12 ± 0.05 ΔE; …" from the run's `m:` refs at `t`, or "Argus hasn't measured anything yet at this moment." when there are none.
- The answer is rendered with `render` (numbers as displays) and the field-name stripper (`unlabelled`); chips are built from `refs_used` exactly as notes build them.

### Prompt `prompts/routine/chat.md`

Answer the researcher's question about this run at the moment given, in at most four short sentences, in plain words (rule 12). Use only the blocks and the picture. Cite every number as a `{ref:<id>}` token; no other digits or number words. Say "consistent with", never "proves". Name the verdict only as one of the levels allowed now. If the data can't answer, say so and say what would answer it. Suggestions are worded as suggestions; never tell the researcher to handle anything hazardous; no medical advice. No headings, no field names, no lists.

## Web

- `lib/types.ts`: `ChatMessage`. `lib/api.ts`: `getChat(runId)`, `askChat(runId, t, question)`; in replay mode `getChat` reads the bundle and `askChat` throws the read-only error.
- `components/chat/ChatPanel.tsx`: the conversation, the suggestions, the input; reads the playhead for `t`; chips reuse `EvidenceChip`. `lib/chat.ts`: pure helpers (the "about 4:12" label, whether to show suggestions, trimming and length checks), tested.
- `RunScreen`: the side column becomes a two-tab panel (Notes | Ask Argus); Notes stays the default.
- The SSE `chat` event appends a message another tab sent.

## Public demo

`export-bundle` records `runs/{id}/chat` like the other GET answers, so saved conversations appear in the demo. Before the next deploy, Aymen asks a few real questions on both demo runs in the app.

## Errors and safety

- No reasoner, the cap, an unknown run: plain HTTP errors shown in words in the panel.
- A model error never crashes anything: it becomes the code-written answer.
- Chat never starts, stops or changes a run, a plan or a device.

## Testing

Worker (pytest, `FakeReasoner`): a clean answer is rendered, chipped and stored; a bare number is rejected and retried; twice rejected gives the code-written answer; an unknown ref is rejected; `t` is clamped; the spend cap returns 409; no reasoner returns 503; the picture is the newest frame at or before `t`; history numbers are masked; the export bundles `chat`; the migration's triggers refuse updates and deletes. Web (node:test): the time label, suggestions shown only when empty, question trimming and limits, replay `askChat` is refused.

## Out of scope

Streaming replies, voice input, a chat on the public link that calls a model, chat outside the Run screen, and the redesign itself (next step).
