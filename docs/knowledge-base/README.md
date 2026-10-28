# Argus knowledge base

Everything decided about Argus before and during the Meta Global AI Developer Hackathon, organized so a person or a coding agent can find one topic fast. Last full update: **Oct 27, 2026**.

## Read order for a new session

1. `00-project-overview.md` (what Argus is)
2. `02-architecture.md` (how it fits together, hard rules)
3. `17-build-plan.md` (what to build today)
4. Then only the file for the task at hand (index below)

## Index

| File | Covers | Read when… |
| --- | --- | --- |
| `00-project-overview.md` | Product, users, differentiators, status, one-liners | Starting any session |
| `01-hackathon-rules-and-dates.md` | Rules, dates, judging, anti-projects, submission, credits | Anything about compliance, deadlines or the demo |
| `02-architecture.md` | Pipeline, hard rules, adapters, who sees what, processes, storage, repo layout | Writing any worker or web code |
| `03-watcher-design.md` | Change detection: what to build, what to skip, presets | Working on capture or triggers |
| `04-models-and-api.md` | Exact Meta API usage: base URL, model IDs, images, video, JSON output, caching, effort, SAM, voice, limits | Writing `segment()` / `reason()` / voice |
| `05-costs-and-credits.md` | Prices, estimates, SAM cost patterns, credits, spend safety | Changing models, frequency or image sizes |
| `06-modes-and-recipes.md` | Analysis modes, recipes format, measurement families, experiment catalog | Adding an experiment type |
| `07-features.md` | Every feature with priority (Must / Should / Later) | Deciding what to build |
| `08-science-rigor.md` | Planning, controls, noise floor, stats, verdict logic, evidence layers, reproducibility, validation | Analysis, verdicts, reports |
| `09-measurement-and-calibration.md` | Argus Card, ArUco, color correction, camera locking on Windows, quality checks, metric methods | Measurement code |
| `10-hardware-and-control.md` | Laptop limits, local SAM, cameras, smart plugs, safety rules, sensors, alerts | Hardware or control code |
| `11-tech-stack-and-libraries.md` | **Verified** library verdicts (use / skip / build), Ax 1.x example, licenses, install | Before adding any dependency |
| `12-skills.md` | Installed Claude Code skills; how Argus uses science skills at runtime | Using or adding skills |
| `13-demo-and-pitch.md` | Framing, anti-project avoidance, demo script, video rules, application answer | Demo, README, video |
| `14-competitors-and-positioning.md` | Lumi, Spectron, self-driving labs, LabOS; positioning | Pitch |
| `15-decisions-log.md` | Every decision with reasons and rejected alternatives | Before changing direction |
| `16-open-questions.md` | Unknowns, day-one checks, questions for office hours | Day one; when blocked |
| `17-build-plan.md` | Day-by-day plan and submission checklist | Every morning |
| `18-glossary.md` | Shared vocabulary | Naming things |
| `19-sources.md` | Every link used | Checking a fact |
| `20-demo-experiment-germination.md` | The chosen demo experiment: design, materials, steps, what Argus measures, import settings | Running, importing or analyzing the demo run |

Related folders: `prompts/` (runtime prompts and JSON schemas), `.claude/skills/` (Claude Code skills), `brand/` (logo, icons, color tokens; read `brand/README.md`), `docs/claude-code-kickoff-prompt.md` (the build brief for Claude Code), `THIRD_PARTY_NOTICES.md`.

## Maintenance rules

- One topic per file; update the file, don't append contradictions.
- When a decision changes, add a new row in `15-decisions-log.md` that supersedes the old one.
- When an open question is answered, tick it in `16-open-questions.md` and move the answer into the right file.
- Facts from the web carry a date; re-check anything older than a week before relying on it.
