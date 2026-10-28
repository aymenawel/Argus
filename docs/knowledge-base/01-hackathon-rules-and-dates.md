# 01 · Hackathon rules, dates and judging

> Source: the official Meta Global AI Developer Hackathon Participant Guide (pasted in full by Aymen). Quotes are exact where marked. All times Eastern (ET).

## Our entry

| Item | Value |
| --- | --- |
| Event | Meta Global AI Developer Hackathon (run by Cerebral Valley) |
| Track | **Indie Developer** (total prize pool $400,000) |
| Problem statement | **Push the Frontier**: "Give a machine a new capability, accelerate a scientific experiment, or unlock a better way to understand and control a physical system." |
| Team | Solo. Team name **Argus Labs** |
| Representative | Aymen (submits the project) |

## Dates

| When (ET) | What |
| --- | --- |
| Mon Oct 26, 12:00 PM | Kickoff |
| Tue Oct 27, 12:00–12:30 PM | Agents 101: Build a Multimodal AI Agent |
| **Wed Oct 28, 12:00–12:30 PM** | **Agents 102: Best Practices for Verifiable Agents** (directly relevant: claim checker, evidence links) |
| Fri Oct 30, 12:00–12:30 PM | Building Specialized Intelligence on Fireworks (Muse open models) |
| Weekdays, 10–11 AM | Office hours in Discord `#office-hours` (text only) |
| Oct 27 – Nov 4 | **Building period** |
| Tue Nov 3 | Last full day for submission questions and troubleshooting |
| **Wed Nov 4, 9:00 PM** | **Submissions due** via the CV platform (late = not considered). Also the deadline to claim the $150 Meta credits |
| Thu Nov 5 – Sun Nov 8 | Judging |
| Mon Nov 9, 12:00 PM | Closing ceremony: top 10 (5 per track) announced, live final-round judging, winners, community vote opens |
| Mon Nov 16 | Community vote winner announced |

## Rules that affect how we build

| Rule (from the guide) | What it means for Argus |
| --- | --- |
| "Repositories **must be public**." | Public from day one. **Never commit API keys**: use `.env` (git-ignored) and `.env.example`. |
| Max 4 per team; solo allowed | Solo is fine. |
| "Your demo **must only highlight the specific features, code, and functionality that you built during the Hackathon**." Failure to identify original contributions = "immediate disqualification at Judges sole discretion." | Every feature in the video must be built Oct 27 – Nov 4. Say so in the README and video. |
| "**New work only**" (only Startups may build on existing code) | First commit on/after Oct 27. Raw camera footage recorded early is fine; all analysis shown must come from hackathon code. |
| Banned: projects that "use code, data, or assets you do not have the rights to" | Respect licenses (see `11-tech-stack-and-libraries.md`, `THIRD_PARTY_NOTICES.md`). |
| Must use Meta models | Muse Spark series, Muse Wonder, Muse Image, Muse Voice Transcribe, SAM 3.1 via Meta Model API; open weights Muse Glimmer and Muse Spark Open; Muse Code agent. |

## Anti-projects (disqualification risk)

Exact list from the guide: medical advice (e.g. AI mental health advisor, skin blemish detector); basic RAG; **simple image analyzers**; **simple "AI for Education" chatbots**; AI job application screener; AI nutrition coach; personality analyzers; sports analyzers or coaches; anything political or involving war.

Argus is not an anti-project as designed, but **"simple image analyzer"** is the one to watch. Always show change over time, calibrated numbers, a verdict and the next-run loop. See `13-demo-and-pitch.md`.

## Submission requirements

- Submit at the CV platform submit page by **Nov 4, 9:00 PM ET**. One submission per team.
- **3-minute demo video** "highlighting the specific features, code, and functionality you built during the Hackathon." It is "one of the primary artifacts Judges use," along with code and the live product.
- Check that the **repo is public**, the **video link is accessible**, and everyone who worked on it is listed.

## Judging

1. **Stage 1 (pass/fail):** project reasonably fits the theme and reasonably used Meta Model API and/or Meta open-weight models, built during the hackathon.
2. **Stage 2:** rubric below, each criterion scored 0–10.
3. **Stage 3:** top 5 per track; final judges watch the videos live and rank them with the same rubric.

### Judging rubric (from the guide, received Oct 27)

| Category | Weight | What judges ask (exact wording) | How Argus scores (see `13-demo-and-pitch.md`) |
| --- | --- | --- | --- |
| **Impact** | **30%** | "What's the real-world potential here? Who benefits, and how much does it matter? Could this actually become something people use? Does it fit into one of the problem statements listed above?" | Access gap (self-driving-lab tools for anyone), reproducibility problem, validation numbers, 5-minute setup with a webcam, a public replay link judges can open, Push the Frontier wording |
| **Use of Meta AI Tooling** | **25%** | "How creatively did this team use Meta's AI tooling? Did they go beyond a basic integration? Did they surface capabilities that surprised even us?" | SAM 3.1 turned into calibrated, zero-shot measurement in mm; multi-day identity tracking; prompts written by Muse from the brief; Spark ↔ Wonder verification; Voice Transcribe for gloved hands; Muse Spark Open; Ax |
| **Technical Depth & Execution** | **20%** | "Is the engineering sound and thoughtfully refined? Does this feel like something that was thought through with real craft." | Claim checker, evidence layers, noise floor and ±, structured outputs, prompt caching, cost logging, validation table |
| **Demo** | **25%** | "Is this a working, impressive demo? Does the product hold up live? Is the demo video genuinely cool to watch?" | Live run + multi-day timelapse with chart overlay, infrared night footage, the "rival explanation caught" moment, Ax + plug closing the loop |

### Prizes

**Indie Developer track ($400,000):** 1st $150K · 2nd $100K · 3rd $75K · 4th $50K · 5th $25K.

**Bonus prizes from Meta ($50K, open to all tracks):**

| Prize | Amount | Rewards | How it's judged | Argus plan |
| --- | --- | --- | --- | --- |
| Most Viral Project | $20,000 | Highest engagement on X after the event | Post the demo on X, submit the post link through the hackathon platform; total likes + reposts + comments **until Nov 8 EOD** | **Target.** Post a short timelapse clip right after submitting (`17-build-plan.md`) |
| Best Build on Meta Open Weight Models | $10,000 | Best project built using **Muse Glimmer or Muse Spark Open**, "served on participants' own hardware or through partner-provided inference" | Flagged in round 1; the **infrastructure partner verifies** the project runs on an eligible open-weight model | Skipped for now; optional later via Baseten (~$24 by card, D-33) |
| Community Vote | $10,000 | Most votes in the public gallery | One vote per verified account; announced Nov 16 | **Target.** Share the gallery link widely |
| Best Agentic Use-Case | $5,000 | Strongest use of AI agents to complete meaningful tasks, make decisions, or coordinate multi-step workflows | Level of autonomy, effectiveness, practical usefulness | **Strong fit.** Decides when to look, what to measure, flags rival causes, picks the next run, acts with limits |
| Best Creative Build | $5,000 | Most original creative project using **Muse Image or Muse Wonder** | Flagged in round 1; originality, execution, how the model is used | Not targeted (Argus uses Wonder for verification, not creative output) |

Startups track ($550K) prize table not received; not relevant to an Indie entry.

## Credits from the guide

| Source | Amount | Notes |
| --- | --- | --- |
| Meta Model API | $150 | **Claimed.** Needs a credit card on the account (temporary pre-authorization charge). Set a **Spend Limit** notification on the Billing page. Each person claims individually by Nov 4, 9 PM. |
| Baseten | $100 + 2M TPM | **Not received.** Per individual. For hackathon use model `meta-models/muse-spark-open-1026` (not the name in their docs). |
| Modal | $100 (first 1,000) | **Not received.** Separately received a **$30 signup credit**, kept as backup. |
| Fireworks | $25 per team | **Not received.** |

## Useful links

- Discord (`#questions`, `#office-hours`, `#announcements`): https://cerebralvalley.ai/e/meta-ai-developer-hackathon/discord
- Livestream: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/live
- Submit: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
- Docs: https://dev.meta.ai/docs/overview · Cookbook: https://github.com/meta-models/meta-model-cookbook
