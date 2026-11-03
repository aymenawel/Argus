# Calm Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The light, calm, one-question-per-screen Argus from the approved mockup, with the public link as a demo mode of the same product.

**Architecture:** Tokens first (every screen inherits the look), then pure helpers with tests (the Argus line, the checks count), then the screens: Run, Results, home and the demo shell. Web only; the worker doesn't change.

**Tech Stack:** Next.js + TypeScript, CSS modules over `styles/tokens.css`, node:test.

**Spec:** `docs/superpowers/specs/2026-11-03-calm-redesign-design.md` (D-98)

## Global Constraints

- Light is the default; Settings offers Light, Dark, System. Colours only through tokens.
- Every number shown comes from stored records; the Argus line is built by code, never by a model.
- Plain words (D-95); anything recorded is labelled "Recorded run · nothing here is live" in the demo.
- No new dependencies. Before every commit: the key scan; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Checks per task: `npm test`, `npx tsc --noEmit -p .`, `npx eslint .`, `npx prettier --check .` in `web/`.

## Review Focus

- A run with no control: the Argus line leads with the most-changed sample and no comparison. Test in Task 2.
- A run with nothing measured yet (live, first seconds): "Argus is watching. Nothing measured yet." Test in Task 2.
- A count metric (sprouted seeds) reads without a unit word ("9 sprouted seeds"). Test in Task 2.
- A viewer whose system is dark and who never chose: light. Test in Task 1.
- Phone width (375 px): no sideways scroll on Run, Results and home. Checked in Task 6.

---

### Task 1: The clean-lab look

**Files:** `web/styles/tokens.css`, `web/lib/theme.ts`, `web/components/shell/ThemeSwitch.tsx`, `web/tests/theme.test.ts`

- [ ] **Test** `readTheme()` returns `"light"` with nothing stored, and `THEME_SCRIPT` sets `data-theme="light"` when nothing is stored.
- [ ] **Implement**: light tokens (spec values) under `:root` and `[data-theme="light"]`; dark tokens under `[data-theme="dark"]` and under `@media (prefers-color-scheme: dark)` for `[data-theme="system"]` only; `ThemeChoice` default `"light"`, storing `"system"` explicitly; ThemeSwitch shows Light, Dark, System.
- [ ] **Check and commit** `feat(web): the clean-lab look, light by default (D-98)`.

### Task 2: The Argus line and the checks count

**Files:** create `web/lib/summary.ts`, `web/tests/summary.test.ts`

**Interfaces:** `argusLine(input: { samples: { label: string; role: "control" | "treatment"; condition: string | null; first: number | null; latest: [number, number] | null }[]; unit: string; verdict: { level: VerdictLevel; sentence: string } | null; checkTime: string | null; running: boolean }): { lead: string; detail: string | null; level: VerdictLevel | null }` and `checkCounts(checks: { ok: boolean | null }[]): string`.

- [ ] **Tests**: the dye run's numbers give "Sample C (test, warm) changed the most: 25.12 ± 0.06 ΔE, against 4.55 ± 0.06 ΔE for the control (B)." and the verdict sentence as `detail`; no control → no "against"; nothing measured → "Argus is watching. Nothing measured yet."; a count unit reads "9 sprouted seeds"-style through `formatPair`; no verdict with a check time → "Argus judges your idea from 2:00."; `checkCounts` → "1 passed · 1 not settled · 1 failed", omitting zero groups.
- [ ] **Implement** with `formatPair`, `unitLabel`, `roleWord`.
- [ ] **Check and commit** `feat(web): the Argus line and the checks count (D-98)`.

### Task 3: The Run screen

**Files:** create `web/components/run/ArgusLine.tsx`, `web/components/run/Scrubber.tsx`, `web/components/run/RunDetails.tsx` (the ⓘ popover); modify `RunScreen.tsx` and its CSS, `RunFrame.tsx` (overlay badges move into RunDetails), `Readouts.tsx` (highlight the most-changed), `NoteCard.tsx` (main sentence + chips, **More** toggles the rest), `PageHeader.tsx` (one status line).

- [ ] Header: crumb, title, status line, See results, Stop run while live. Remove the Badge/Spend clutter from the header.
- [ ] ArgusLine under the header from `argusLine` (snapshot readings at the playhead's end, the run's verdict).
- [ ] Workspace: picture + sample cards + Scrubber on the left, SidePanel on the right; drop the Timeline and Verdict panels from the Run screen.
- [ ] **Check** on the live app (dye run, seed plate) at 1440 px; commit `feat(web): a calm Run screen (D-98)`.

### Task 4: The Results screen

**Files:** modify `ResultsScreen.tsx` and its CSS, `NextRunCard.tsx`; reuse `ArgusLine`, `VerdictPanel`.

- [ ] Order: header (Back to the run), ArgusLine with the verdict, Curves, "What Argus checked" (`checkCounts` line opening the VerdictPanel in a `<details>`), Next run tiles with the first sentence and a **Why** `<details>`, Numbers `<details>` (fitted values, label comparison), Videos.
- [ ] **Check** both runs; commit `feat(web): a calm Results screen (D-98)`.

### Task 5: Home and the demo

**Files:** create `web/components/experiments/ExperimentCard.tsx`; modify `app/page.tsx`, `app/replay/ReplayIndex.tsx` and page, `app/replay/[runId]/ReplayRun.tsx`, `components/shell/Rail.tsx`; delete `components/replay/ReplayBanner.*`.

- [ ] ExperimentCard: latest picture, title, status line, verdict tag, link; used by home and the demo list.
- [ ] Demo: list titled "Experiments" with the built-in-the-hackathon line; rail Experiments → `/replay`, a **Demo** tag; run pages' status line says "Recorded run · nothing here is live"; crumbs say Experiments; banner removed.
- [ ] **Check** the demo preview (port 3001) and the app; commit `feat(web): one product, with a demo mode (D-98)`.

### Task 6: Every screen, both widths

- [ ] Render home, Run, Results (both runs) and the setup wizard's first step in the app and the demo at 1440 px and 375 px; fix overflow and leftovers; send Aymen the screenshots.
- [ ] Full web checks; update `docs/knowledge-base/15-decisions-log.md` (D-98) and `07-features.md`; commit `docs: the calm redesign (D-98)`.
