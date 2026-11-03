# Ask Argus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A chat beside the notes on the Run screen that answers questions about the moment on the playhead, live or rewatching, with every number taken from Argus's own readings.

**Architecture:** A new evidence record (`chat_messages`), a task builder next to `note_task`, and `pipeline/chat.py` that builds the moment's context, calls the routine reasoner once (one retry), checks the answer with the claim checker and falls back to a code-written answer. Two routes (`GET`/`POST /api/runs/{id}/chat`), a bundle entry for the demo, and a `ChatPanel` in a Notes | Ask Argus tab pair.

**Tech Stack:** Python 3.12 worker (FastAPI, SQLite, pytest, `FakeReasoner`), Next.js + TypeScript web (node:test, tsc, eslint, prettier).

**Spec:** `docs/superpowers/specs/2026-11-03-ask-argus-chat-design.md` (D-97)

## Global Constraints

- The model never computes numbers: an answer's numbers are `{ref:<id>}` tokens from `build_refs` and must pass `check_text_fields`.
- Models are called only through the worker's reasoner (`jobs.reasoner`, i.e. `reason()`); routine tier; function name `chat`; every call logged with `add_model_call`.
- Prompt text lives in `prompts/routine/chat.md`; the schema in `prompts/schemas/chat_answer.json`.
- Chat records are evidence: no update, no delete, no replace (triggers, as `009_next_runs.sql`).
- Plain words on screen and in answers (D-95, rule 12). No new dependencies.
- `EXPECTED_CHAT_USD = 0.01`; questions 1–500 characters after trimming; history = the run's last 6 messages; at most 4 sentences per answer (prompt rule).
- Before every commit: the key scan; commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A question on a run with no frames or readings yet (a live run's first seconds): an answer or the fallback "Argus hasn't measured anything yet at this moment.", never a crash; no picture is sent. Test in Task 3.
- An answer that starts with its field name ("Answer: …"): shown without it. Test in Task 3.
- A blank or 501-character question: refused with 422 before any model call. Test in Task 4.
- An old demo bundle with no `chat.json`: the panel shows an empty saved conversation, not an error. Test in Task 5.
- A model error or timeout: the code-written answer, the call still logged. Test in Task 3.

---

### Task 1: The chat record

**Files:**
- Create: `worker/argus/storage/migrations/012_chat.sql`
- Modify: `worker/argus/domain.py` (after `NoteAttempt`), `worker/argus/storage/repos.py` (after the note functions)
- Test: `worker/tests/test_chat.py`

**Interfaces:**
- Produces: `ChatMessageDraft(Record)`: `t: float (ge=0)`, `question: str`, `answer: str`, `body: dict[str, Any]`, `check_status: Literal["passed", "fallback"]`, `model_call_id: str | None`. `ChatMessage(ChatMessageDraft)`: `id: str`, `run_id: str`, `created_at: datetime`. `repos.add_chat_message(db, run_id, draft) -> ChatMessage` (id `new_id("chat")`, `created_at` now in UTC, as `add_next_run` sets it); `repos.chat_for_run(db, run_id, limit: int | None = None) -> list[ChatMessage]` oldest first (`limit` keeps the newest `limit`, still oldest first). `CHAT_JSON = ("body",)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_chat.py`: `test_a_chat_message_is_stored_and_listed_oldest_first` (two messages at t 60 and 30 added in that order come back in insertion order, `limit=1` returns only the second); `test_chat_messages_are_evidence` (`UPDATE chat_messages SET answer='x'` and `DELETE FROM chat_messages` each raise `sqlite3.IntegrityError` matching "chat messages are evidence"). Use `tests.records.finished_run(db, tmp_path)` for the run.
- [ ] **Step 2: Run** `uv run pytest tests/test_chat.py -q` → FAIL (no `ChatMessageDraft`).
- [ ] **Step 3: Implement** the migration (`chat_messages`: id, run_id → runs, t, question, answer, body, check_status CHECK IN ('passed','fallback'), model_call_id, created_at; index `(run_id, t)`; the three triggers with message 'chat messages are evidence'), the two records and the two repo functions.
- [ ] **Step 4: Run** `uv run pytest tests/test_chat.py tests/test_storage.py -q` → PASS.
- [ ] **Step 5: Commit** `feat(chat): the chat message record (D-97)`.

### Task 2: The prompt, schema and task

**Files:**
- Create: `prompts/routine/chat.md`, `prompts/schemas/chat_answer.json`
- Modify: `worker/argus/reason/prompts.py` (after `note_task`), `prompts/README.md` (list the new prompt)
- Test: `worker/tests/test_prompts.py`

**Interfaces:**
- Consumes: `ChatMessage` (Task 1).
- Produces: `chat_task(recipe, plan, refs, events, notes, history: Sequence[ChatMessage], question: str, *, t_display: str, allowed: Sequence[str], verdict: Verdict | None = None, rejected: Sequence[str] = (), experiment_id: str | None = None, labels: Mapping[str, str] | None = None) -> ReasonTask` with `function="chat"`, `stable=_stable(recipe, plan)`, `variable=(measurements_block(refs), events_block(events, refs, labels), notes_block(notes), history_block(history), "ALLOWED VERDICTS NOW: …", verdict line or "VERDICT: none yet", f"MOMENT ASKED ABOUT: {t_display}", task text with rejections, f"QUESTION: {question}")`. `history_block(history) -> str`: "CONVERSATION SO FAR: none" or lines "- Q: … / A: …" with `NUMBER.sub("[n]", …)` on both.
- Schema `chat_answer.json`: strict object, `answer: string`, `refs_used: string[]`, both required, no other keys.

- [ ] **Step 1: Write the failing tests** in `tests/test_prompts.py`: `test_a_chat_task_puts_the_question_last_and_masks_old_answers` (history answer "Glass C is at 25.1 ΔE" appears as "Glass C is at [n] ΔE"; `task.variable[-1] == "QUESTION: Why is C orange?"`; `task.function == "chat"`; `task.stable == note_task(...).stable` for the same recipe and plan); `test_the_chat_prompt_uses_plain_words` (`load_prompt("routine/chat.md")` contains "{ref:" and "rule 12" and none of "vessel", "treatment", "noise floor").
- [ ] **Step 2: Run** `uv run pytest tests/test_prompts.py -q -k chat` → FAIL.
- [ ] **Step 3: Write** the prompt (the spec's "Prompt" section, as task text after the blocks) and the schema; implement `history_block` and `chat_task`.
- [ ] **Step 4: Run** `uv run pytest tests/test_prompts.py -q` → PASS (the method-card word test included).
- [ ] **Step 5: Commit** `feat(chat): the chat prompt and task (D-97)`.

### Task 3: Answering a question

**Files:**
- Create: `worker/argus/pipeline/chat.py`
- Test: `worker/tests/test_chat.py`

**Interfaces:**
- Consumes: Tasks 1–2; `build_refs`, `allowed_now`, `first_locked_plan`, `latest_verdict`, `events_for_run` (filtered to `NOTABLE`), `notes_for_run`, `frames_for_run`, `snapshot_jpeg`, `check_text_fields`, `schema_errors`, `render`, `unlabelled`, `add_model_call`, `run_spend_usd`, `format_run_time`.
- Produces: `class ChatRefused(Exception)`; `EXPECTED_CHAT_USD = 0.01`; `async def ask_chat(db, settings, run, recipe, reasoner, t: float, question: str) -> ChatMessage`. Raises `ChatRefused("This run has reached its spending limit")` when `run_spend_usd + EXPECTED_CHAT_USD > settings.run_spend_cap_usd` (no call made). `clamp_t(frames, t) -> float` (0 when no analysed frame).

- [ ] **Step 1: Write the failing tests** (all `@pytest.mark.anyio`, `FakeReasoner`, `tests.records.finished_run(db, tmp_path)`, settings with `ARGUS_DATA_DIR=tmp_path`):
  - `test_a_clean_answer_is_rendered_chipped_and_stored`: answer `{"answer": "Glass B changed by {ref:m:B:delta_e}.", "refs_used": ["m:B:delta_e"]}` → `message.answer` has no "{ref:", `check_status == "passed"`, `body["chips"][0]["ref"] == "m:B:delta_e"`, `logged_functions(db) == ["chat"]`, one picture sent (`reasoner` saw `images` of length 1).
  - `test_a_free_number_is_retried_then_written_by_code`: two answers with "about 12 units" → `reasoner.calls == 2`, `check_status == "fallback"`, answer starts "I couldn't answer that without guessing a number." and contains "Sample A".
  - `test_a_model_error_gives_the_code_written_answer`: `ReasonError` then nothing → fallback, the failed call logged.
  - `test_the_moment_is_clamped_to_the_run`: `t=1e9` → `message.t == ` the last frame's t; `t` passed in the task's "MOMENT ASKED ABOUT".
  - `test_an_answer_starting_with_its_field_name_reads_without_it`: "Answer: the glass is clear." → "The glass is clear."
  - `test_a_run_with_nothing_measured_yet`: `finished_run(..., frames=1, readings=False)` and a fallback path → "Argus hasn't measured anything yet at this moment."; a run with no frames at all sends no picture.
  - `test_the_spending_limit_refuses_before_any_call`: settings with `ARGUS_RUN_SPEND_CAP_USD` below the run's spend → `ChatRefused`, `reasoner.calls == 0`.
  - `test_the_last_six_messages_are_the_history`: 7 stored messages → the task's history block holds the newest 6.
- [ ] **Step 2: Run** `uv run pytest tests/test_chat.py -q` → the new tests FAIL.
- [ ] **Step 3: Implement** `ask_chat` in this order: spend check; frames → `clamp_t`; refs, plan, events, notes, verdict (latest at or before t), allowed levels, labels, history (`chat_for_run(limit=6)`); picture from the newest analysed frame at or before t (`cv2.imread` of `settings.data_dir / frame.path`, then `snapshot_jpeg(image, settings.snapshot_px)`); up to two attempts (call, `schema_errors`, `check_text_fields(data, ["answer"], refs)`, every `refs_used` id in refs; rejections passed to the second task); on success `render(unlabelled(answer, "answer"), refs)` and chips built as `NoteWriter._add` builds them; otherwise `fallback_answer(refs, t_display)`; log every call; store with `add_chat_message`. A model call whose `ReasonError` carries a call is logged too.
- [ ] **Step 4: Run** `uv run pytest tests/test_chat.py -q` → PASS.
- [ ] **Step 5: Commit** `feat(chat): answer a question about the moment on screen (D-97)`.

### Task 4: Routes, live updates and the demo bundle

**Files:**
- Create: `worker/argus/api/chat.py`
- Modify: `worker/argus/api/app.py` (register beside the note routes), `worker/argus/export/bundle.py` (record `f"{run_path}/chat"` after notes)
- Test: `worker/tests/test_chat.py`, `worker/tests/test_bundle.py`

**Interfaces:**
- Consumes: Task 3.
- Produces: `register_chat_routes(app, *, db, broker, settings, jobs, recipes)`. `ChatIn(BaseModel)`: `t: float = Field(ge=0)`, `question: str` stripped, 1–500 characters (validator). `GET /api/runs/{id}/chat → list[ChatMessage]`; `POST → 201 ChatMessage`, 404 unknown run, 503 "reasoning is off: MODEL_API_KEY is not set", 409 with the `ChatRefused` text. After storing, `broker.publish("chat", {"run_id": …, "message": …})`.

- [ ] **Step 1: Write the failing tests**: `test_chat_over_the_api` (POST 201 then GET lists it; `logged_functions(db) == ["chat"]`); `test_a_blank_or_long_question_is_refused` ("   " and "x" * 501 → 422, `reasoner.calls == 0`); `test_chat_without_a_key_is_503` (`reasoner=None`); `test_an_unknown_run_is_404`; in `test_bundle.py`, `test_the_bundle_keeps_the_chat` (a stored message appears in `runs/<id>/chat.json`).
- [ ] **Step 2: Run** `uv run pytest tests/test_chat.py tests/test_bundle.py -q` → the new tests FAIL.
- [ ] **Step 3: Implement** the routes, the registration and the bundle line.
- [ ] **Step 4: Run** the full worker suite in the background: `set -o pipefail; uv run pytest -q -p no:cacheprovider` → all pass; `uv run ruff check argus tests` and `uv run ruff format --check argus tests` clean.
- [ ] **Step 5: Commit** `feat(chat): chat routes, live updates and the demo bundle (D-97)`.

### Task 5: Web data layer

**Files:**
- Create: `web/lib/chat.ts`, `web/tests/chat.test.ts`
- Modify: `web/lib/types.ts` (`ChatMessage`), `web/lib/api.ts` (`getChat`, `askChat`), `web/lib/events.ts` (add `"chat"`)

**Interfaces:**
- Produces: `type ChatMessage = { id; run_id; t: number; question: string; answer: string; body: { answer?: string; refs_used?: string[]; chips?: NoteChip[] }; check_status: "passed" | "fallback"; model_call_id: string | null; created_at: string }` (`NoteChip` is the chip type notes already use). `getChat(runId): Promise<ChatMessage[]>` (in replay mode a missing file resolves to `[]`); `askChat(runId, t, question): Promise<ChatMessage>` (POST; refused in replay by the existing read-only error). In `lib/chat.ts`: `momentLabel(t: number, span: number): string` → `about ${formatRunTime(t, span)}`; `cleanQuestion(text: string): string | null` (trimmed, null when empty or over 500); `SUGGESTIONS = ["What's happening now?", "Which sample is changing the most?", "Can Argus judge the idea yet?"] as const`; `showSuggestions(messages: ChatMessage[]): boolean` (true when empty).

- [ ] **Step 1: Write the failing tests** in `chat.test.ts`: `momentLabel(252, 1250) === "about 4:12"`; `cleanQuestion("  hi ") === "hi"`, `cleanQuestion("   ") === null`, `cleanQuestion("x".repeat(501)) === null`; `showSuggestions([]) === true`; and with `NEXT_PUBLIC_ARGUS_REPLAY=1` and no bundle file, `getChat` resolves `[]` (stub `fetch` to 404, as the replay tests do).
- [ ] **Step 2: Run** `node --test tests/chat.test.ts` → FAIL.
- [ ] **Step 3: Implement** the type, the two API functions, the helpers and the event name.
- [ ] **Step 4: Run** `npm test`, `npx tsc --noEmit -p .`, `npx eslint .`, `npx prettier --check .` → all clean.
- [ ] **Step 5: Commit** `feat(web): chat types, calls and helpers (D-97)`.

### Task 6: The Ask Argus tab

**Files:**
- Create: `web/components/chat/ChatPanel.tsx`, `web/components/chat/ChatPanel.module.css`
- Modify: `web/app/experiments/[id]/run/RunScreen.tsx` (the Notes panel becomes a two-tab panel), its CSS module

**Interfaces:**
- Consumes: Task 5; `usePlayhead`, `EvidenceChip`, `useReadOnly`, `subscribe` from `lib/events.ts`.
- Produces: `ChatPanel({ runId, span }: { runId: string; span: number })`.

- [ ] **Step 1: Build the panel**: load with `getChat`; list oldest first, each with the question, the answer, `momentLabel` and its chips; suggestions when empty (a click fills and sends); a textarea + Send (Enter sends, Shift+Enter breaks a line); while waiting "Argus is looking…" and the input disabled; on error the `errorText` under the box with the question kept; a fallback answer is marked "Written by code"; the SSE `chat` event appends a message for this run if not already listed; read-only: label "Saved questions from the app", no input, hint "Ask your own questions in the app". Tabs: two buttons with `role="tab"`/`aria-selected`, Notes default; the tab choice is per page view only.
- [ ] **Step 2: Check it for real**: worker and web previews running; on the dye run (`run_d8f8b410078e`) ask "What's happening now?" at the end and at 2:00, confirm a plain answer with working chips; confirm the replay preview shows the saved messages read-only after re-exporting the bundle. Check a phone width (375 px).
- [ ] **Step 3: Run** `npm test`, `npx tsc --noEmit -p .`, `npx eslint .`, `npx prettier --check .` → clean.
- [ ] **Step 4: Commit** `feat(web): the Ask Argus tab beside the notes (D-97)`, then update `docs/knowledge-base/07-features.md` (one line under the Run view) and commit `docs(chat): Ask Argus in the features list`.
