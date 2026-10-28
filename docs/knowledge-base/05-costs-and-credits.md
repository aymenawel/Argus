# 05 · Costs and credits

> Prices verified on https://dev.meta.ai/docs/pricing-rate-limits on **Oct 27, 2026**. Estimates are planning numbers; replace them with real `usage` numbers after the day-one token test.

## Prices

| Model | Input / 1M | Cached input / 1M | Output / 1M |
| --- | --- | --- | --- |
| `muse-spark-1.3` (standard) | $1.25 | $0.15 | $4.25 |
| `muse-spark-1.3-contributor` | $0.10 | $0.002 | $0.20 |
| `muse-wonder-1.0` | $4.00 | $0.20 | $20.00 |

| Other | Price |
| --- | --- |
| SAM 3.1 image segmentation | $2.50 per 1,000 images (= $0.0025 per request, **per concept**) |
| SAM 3.1 video segmentation | $0.20 per 1,000 frames, **minimum 50 frames per request** |
| Muse Voice Transcribe | $0.18 per hour of audio |
| Muse Image | $0.01 per image (not planned) |

Reasoning tokens are billed as output tokens.

## Planning estimate for the whole build (rechecked)

Assumptions: 3,000 reasoning calls; each 6,000 input tokens (text + 2 snapshots) and 300 output tokens; tiered = 90% routine, 10% deep with 1,000 output tokens; SAM 20 h at 1 frame/s = 72,000 frames; voice ~$1 (now known to be far less).

The 2-snapshot guess holds up: Meta's docs say a ~1280 px image is ~1,300–1,500 tokens.

| Setup | Calculation | Total |
| --- | --- | --- |
| **Tiered (chosen):** Spark routine + Wonder deep | Routine in 2,700×6,000×$1.25/M = $20.25 · out 2,700×300×$4.25/M = $3.44 · Deep in 300×6,000×$4/M = $7.20 · out 300×1,000×$20/M = $6.00 · SAM $14.40 · voice ~$1 | **≈ $52.30** |
| All Muse Wonder | in 18M×$4 = $72 · out 0.9M×$20 = $18 · SAM $14.40 · voice ~$1 | ≈ $105.40 (≈ $109.60 with longer deep outputs) |
| All Muse Spark standard | reasoning ≈ $26 + SAM + voice | ≈ $42 |
| Contributor tier + SAM API | reasoning ≈ $2 + SAM $14 + voice | ≈ $17 |

**Risk:** if images cost twice the guess, all-Wonder ≈ $178 (over the $150 credit); tiered ≈ $80 (safe).

**Savings levers:** prompt caching (stable prefix first; cached Spark input is 8× cheaper), smaller snapshots (768 px), `reasoning.effort="low"` for routine notes, collapse repeated "no change" notes, Smart trigger mode for long runs.

## SAM cost patterns

| Pattern | Cost |
| --- | --- |
| Smart trigger, image mode: 200 triggers/day × 2 concepts | 400 × $0.0025 = **$1.00/day** |
| Continuous, image every 5 s for 10 min, 1 concept | 120 × $0.0025 = **$0.30** |
| Video mode, 10-min clip **downsampled to 1 fps** (600 frames) | **$0.12** |
| Video mode, same clip at 30 fps (18,000 frames) | Over the 15,000-frame limit; split or downsample |

Rule: **downsample video to 1–2 fps before sending to SAM**, and batch short events into one request where possible (50-frame minimum).

## Why runtime skills are not loaded into prompts

The 7 relevant skills total ~21,000 tokens. Adding them to 3,000 Spark calls ≈ **+$78**. Argus sends a ~350-token rules block instead (`prompts/system/scientific-rules.md`).

## Credits status

| Source | Status | Use |
| --- | --- | --- |
| Meta Model API $150 | **Claimed** | Everything runs here first |
| Modal $30 signup credit | Received | Backup only (self-hosted SAM if Meta credits run low or the API fails during the demo) |
| Modal $100 | **Not received** | — |
| Baseten $100 + 2M TPM | **Not received** | Routine tier on Muse Spark Open (D-27) would be **paid by card on Baseten**: about 2,700 calls × (6,000 in + 300 out tokens) ≈ $20.25 + $3.44 ≈ **$24 out of pocket**, while Meta's credit then covers only deep tier + SAM + voice (≈ $28). **Skipped for now, kept as an option (D-33)** |
| Fireworks $25 | **Not received** | — |

Partner credits are **not needed** to finish Argus. They are backups and a way to add more Meta models if time allows.

## Safety settings

- [ ] Set a **Spend Limit** notification on the Meta Billing page (e.g. at $100).
- [ ] Log tokens and cost for every call in `model_calls`; show a running total in the dashboard.
- [ ] Hard stop in code if a run's spend passes a configured cap (protects against a loop bug).

## Form answers already given (for consistency)

- Modal: "Inference on open-weight models via Endpoints" + Others ("Serverless GPU functions for video frame processing and SAM 3.1 video tracking that scale to zero between experiment events"); estimated compute $50–100.
- Baseten: request volume **Moderate**.
- Fireworks: goals "Prototype with open models" + "Faster speeds or lower costs"; use cases "Agentic AI" + Other (vision-based experiment monitoring).
