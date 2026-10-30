# 13 · Demo and pitch

## Framing [decided]

Pitch Argus as **self-driving-lab intelligence for anyone with a webcam**: it plans an experiment, watches it, measures it in real units, judges the hypothesis and picks the next run. **The loop is the product; the camera is one input.** Existing products (Lumi, self-driving labs) prove the need; Argus brings it to people who can't afford them.

Theme fit, almost word for word: Push the Frontier = "accelerate a scientific experiment" + "understand and control a physical system."

## Scoring plan against the rubric

| Criterion (weight) | What to show | Concrete evidence to prepare |
| --- | --- | --- |
| **Impact (30%)** | Who benefits (students, teachers, small labs, hobby scientists) and why it matters (missed events, subjective judging, reproducibility) | The access-gap line; the 70% / 50% reproducibility survey numbers; the validation table; "5-minute setup with an under-$30 webcam and a printed card"; a **public replay page** judges can open without hardware; ideally one real person (a teacher or lab instructor) trying it, with a one-line quote |
| **Use of Meta AI Tooling (25%)** | Go beyond "call a model": surprising capabilities | SAM 3.1 turned into **zero-shot measurement in mm** (card + masks, no training); identity tracking across a multi-day run; SAM concept prompts written by Muse from the plain-language brief; **Muse Wonder checking Muse Spark** (verifiable agent); Muse Spark reading short video clips; Voice Transcribe for notes with gloved hands;  Ax (Meta open source) choosing the next run; infrared night frames segmented by SAM |
| **Technical Depth & Execution (20%)** | Craft | Claim checker, four evidence layers, noise floor and ±, strict JSON schemas, prompt caching with cache-hit numbers, per-call cost log, tamper-evident hash chain, clean adapters, README with architecture diagram |
| **Demo (25%)** | Working, live, cool to watch | Live run that holds up; 3-day timelapse with the chart drawn over it; IR night clip; the "caught a rival explanation" moment; Argus switching a lamp by itself; tight 3-minute edit |

## Bonus prizes we target

| Prize | Plan | Deadline |
| --- | --- | --- |
| Best Build on Meta Open Weight Models ($10K) | **Entered (D-77).** Drafting from words and run notes run on Muse Spark Open via Baseten, switchable in Settings; show the switch and a note labelled Muse Spark Open in the video | — |
| Best Agentic Use-Case ($5K) | Show autonomy step by step: decides when to look, what to measure, flags a confounder, asks the researcher a question, proposes and (with approval) executes the next action | Nov 4 |
| Most Viral Project ($20K) | Post a 20–30 s clip on X right after submitting: the multi-day timelapse with measurements overlaid ("3 days of seeds in 25 seconds, measured by AI"); tag the hackathon/Meta accounts; submit the post link on the platform; share in Discord and with friends/classmates | Engagement counts **until Nov 8 EOD** |
| Community Vote ($10K) | Share the public gallery link (tutoring network, school, Discord, social) | Votes until results Nov 16 |

## Public replay page (helps Impact, Demo, Community Vote, Viral)

Judges and voters don't have the hardware. Publish a read-only page for one finished run: timelapse with overlay, timeline of events and notes, charts, verdict, and the validation table. Static export of the dashboard on Vercel is enough. Link it from the README, the submission and the X post.

## Staying clear of anti-projects

| Risk | How Argus avoids it |
| --- | --- |
| Simple image analyzer (**the one to watch**) | Never demo a single photo description. Show change over time, calibrated numbers, a live chart, a verdict and the next run |
| AI-for-education chatbot | Pitch as a research tool. Students can use it; the product is measurement and experiment control, not tutoring |
| Medical advice | No clinical or health claims; no "analyze your skin cells" demos. Cell assays framed as lab research only |
| Unsafe experiments | Wizard safety check flags hazards and blocks automatic control for them |

## What makes it "frontier"

- **Verifiable agent:** every AI claim checked against the data and linked to evidence (matches the Agents 102 "Verifiable Agents" session).
- **Closed-loop experimentation:** Ax + smart plug move Argus from watching to acting, like self-driving labs (Toronto's Ada, Argonne), on a desk.
- **Several Meta models working together:** SAM 3.1 (masks), Muse Spark (routine notes), Muse Wonder (verdicts, critique), Muse Voice Transcribe (voice notes). Ax is Meta open-source too.

## 3-minute demo script [draft]

| Time | Beat |
| --- | --- |
| 0:00 | **The problem:** researchers miss overnight events and judge by eye (hook: "3 days of an experiment in 20 seconds" highlights reel) |
| 0:20 | **Setup:** card in frame; Argus finds four cups, labels control and treatments, shows the measurement preview; plan locked |
| 0:50 | **Live run:** a fast reaction; notes, curves and "time to target" appear |
| 1:30 | **The catch:** lighting changes or the control also moves; Argus flags a rival explanation instead of calling a false success |
| 2:00 | **The long run:** imported multi-day germination footage → curves, verdict with error bars, timelapse with overlay |
| 2:30 | **The loop:** Ax proposes the next batch and Muse explains the pick (multi-round loop on the fast experiment, D-42); validation slide (accuracy, events caught). No smart plug this hackathon (D-44) |
| 2:50 | **Close:** one webcam and a printed card did what usually needs an expensive imaging system. "Everything shown was built Oct 27 – Nov 4." |

## Video rules

- Under 3 minutes; best material in the first 30 seconds.
- Every number and event comes from a real run. Anything simulated or sample data is labeled on screen.
- Show only features built during the hackathon; say so in the video and README.
- Protect the last two days for recording and editing; never cut demo time.

## Start a long experiment today

Slow features need real footage by demo day. Run the chosen **salt-stress germination dose-response** (3 salt levels × 2 jars, side view) on the **Canon XA50 in fast motion** on AC power; full protocol in `20-demo-experiment-germination.md`. Show it in the video as a **labeled replay** ("recorded Oct 27–30, analyzed by Argus, 600× speed") plus one short genuinely live moment. Argus analyzes it later through Import video with the time-scale factor. Record only raw footage early; all analysis shown must come from hackathon code. Optional second run on the webcam: yeast fermentation or salt crystals.

## Application answer (submitted wording, for consistency)

> I want to build **Argus**, an AI lab partner that watches your experiment so you don't have to. It's named after the hundred-eyed watchman of Greek myth.
>
> Today, AI that monitors and reasons about experiments only exists in multimillion-dollar "self-driving labs" and enterprise systems. Students, teachers, and small research teams don't have access to it. Argus brings that to anyone with a webcam.
>
> Picture a webcam pointed at a jar of fermenting yeast. You tell Argus your hypothesis: "warmer water makes it rise faster." Then you walk away. **SAM 3.1** tracks the foam as it climbs, and Argus logs every change with a timestamp and a snapshot. When you come back, you watch a 20-second highlights reel instead of six hours of footage. **Muse Spark** has written notes like *"2:14 PM: foam hit 3 cm, ahead of schedule, supporting your hypothesis,"* and it suggests what to try in your next run.
>
> It works the same with a plant, crystals, or a USB microscope, and it only calls the AI when something changes, so even week-long experiments stay cheap. In Plant mode, it can switch on a grow light by itself.

## Writing style for public posts

Plain and straightforward. Use "Argus Labs" as the team; don't say "we" (solo); avoid dramatized example scenes that read as AI-written.
