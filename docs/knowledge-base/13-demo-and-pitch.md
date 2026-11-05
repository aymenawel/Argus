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

## Making the video [decided Nov 3, D-96; storyboard waits for Aymen's idea]

- **Who and how:** Claude builds the whole video in code with HyperFrames (Apache-2.0; its Claude Code skills are installed). Narration is an AI voice made locally (`npx hyperframes tts`); Aymen approves a short sample first.
- **Footage:** real Argus runs (the dye run, the Genze seed plate, the E. coli swarms with their CC BY credit) plus professional experiment footage found online to show the idea. Online footage only with a reuse licence (Pexels, Pixabay, Wikimedia Commons CC BY/CC0, NASA public domain), credited at the end. Footage Argus didn't analyse never carries Argus's outlines or numbers unless Argus really ran on it (an import works on any video, ~$0.50–1.50 each) or the shot says "Illustration".
- **Screens:** sharp captures of the real replay pages (headless Chrome) with camera moves through them, zooming into the part that matters; never a redrawn, made-up dashboard. Plan B for live motion: obs-mcp (below).
- **Sound and mix:** small sounds only on things that matter (a tick when a check passes, the counter while a number rolls, a chime on the last card), none on cards sliding in, about 20 dB under the voice. The voice at least 12 LU over music and effects; master at −14 LUFS, true peak under −1 dB.
- **Workflow:** a base cut first, then fix one moment at a time; say the moment by the words spoken, not by seconds.

### Resources reviewed (Nov 3)

| Resource | Verdict |
| --- | --- |
| Motion Graphics with Claude Code, PDF + starter kit (Damiano Caudullo) | **Use as a guide.** A HyperFrames tutorial. Its 9 sounds (made in code, "no licence to worry about") and its OFL fonts are copied to `data/video-kit/` (git-ignored, not redistributed). Take the method (PROMPT 10: build around real screenshots; Fix 06: move through the real screens). Skip its four styles: the video matches Argus's own look so judges recognise the app |
| [showheyohtaki/motion-prompt](https://github.com/showheyohtaki/motion-prompt) | **Skip for now.** 192 named effects with Canvas code (MIT); HyperFrames' own animation skill and ~450 registry blocks cover this. Open it only to find a name for a specific effect |
| [royshil/obs-mcp](https://github.com/royshil/obs-mcp) | **Plan B.** Lets Claude start and stop OBS recording and switch scenes (GPL-2.0, a tool, not shipped). OBS is installed; Aymen would enable OBS's WebSocket server and set its password himself, add the server to the Claude config and restart. The recorded window must be in front |
| [prompt-motion.com](https://prompt-motion.com/) | **Inspiration only.** A gallery of motion clips made with Claude, with their prompts (Product UI, Charts, Diagrams). Aymen can point at 2–3 clips whose feel he likes |

### Ad references (processed by Aymen, Nov 3)

Five professional launch ads, broken down shot by shot with frames and transcripts, in Aymen's local folder
`C:\Users\aymen.LIGER\No-Code projects\Reels\knowledge\sections\ads-inspiration` (not copied here: they are other
companies' ads, for reference only): OpenAI ChatGPT Work "Sites" (29 s, silent), Anthropic Claude Cowork (69 s,
silent), Google Canvas in Gemini (60 s, silent, dark with glow), Google Gemini for business (102 s, silent, pastel,
blur-to-sharp type), Google "Welcome to the Gemini era" (60 s, voiced, live action). What to take for Argus:

| Pattern (seen in) | Argus's version |
| --- | --- |
| **One task told end to end** instead of a feature montage (Cowork) | Follow one experiment: three glasses set up → watched → measured with ± → a question asked → the honest verdict → the next run |
| **Escalation**: each example more impressive, the strongest last (Canvas) | Dye run first (simple, visual), then the seed plate (published data, curves, a statistical next run), the models working together last |
| **Bookends**: mark → one bold line → the product → mark + link (all of them) | The Argus eye mark → one plain line → … → mark + `argus-replay.vercel.app` as the call to action |
| **Short type cards** between beats, built word by word or blur-to-sharp (Canvas, Gemini for business) | Plain one-liners in Inter on the light canvas: "It measures." "It checks itself." "It tells you what to try next." |
| **Real UI, not mockups**; the screen recording is the proof (Sites) | Real captures of the redesigned app and demo, with camera moves into the part that matters (already D-96) |
| **A calm "working" state**: plain "Thinking" text, a checklist that ticks (Sites, Cowork) | Ask Argus's "Argus is looking…", the verdict's checks ticking passed / not settled / failed from the real check list, "✓ numbers checked" on an answer |
| **Agents made visible**: a labelled node and a glowing connector line (Gemini for business) | A 4–5 s diagram: SAM 3.1 outlines → code measures → Muse Spark writes → the claim checker → Muse Wonder judges and critiques → Ax and Muse pick the next run |
| **One repeated AI signature** across screens (Gemini's pill button) | The Argus eye mark and the "Ask Argus" pill, the same every time they appear |
| **Fine print on sped-up footage** (Canvas: "Sequences shortened") | A small line wherever footage is sped up or replayed: "Recorded run, shown 60× faster; every number is Argus's own measurement" |
| **One accent per scene on a neutral base** (Sites) | The light clean-lab canvas with teal on the data, as in the app |
| **A plain closing call to action with the link** (Canvas, Gemini) | "Open the demo: argus-replay.vercel.app", with "Built Oct 27 – Nov 4" |

Differences to respect: four of the five are silent and 30–70 s long; Argus's video is up to 3 minutes for judges and
has an AI voice (D-96), so the voice carries the longer explanation while the pacing follows these ads (1–3 s cuts in the
hook, longer holds on the UI beats). Their dark-glow look (Canvas) doesn't match Argus's light app and is not used.

### Cut 1 (Nov 4, D-100)

The project lives in git-ignored `data/film/argus-film/` (HyperFrames; `SPEC.md`, `REVIEW.md`, one scene per file in
`compositions/`); the footage and the ElevenLabs key file stay out of the repo.

- **Story (1:51):** one experiment end to end. A clock reaction's goal ("switch at exactly 30 seconds") → Argus plans a
  fair test and locks it → watches three repeats → checked notes and a rejected invented number → Ask Argus → verdict
  "Supported" (repeatable within 0.2 s) → next run (about half the iodate) → the five-step loop → under the hood →
  the real demo and the link.
- **Footage:** DIY bama, "Black Magic Water! (Iodine Clock Reaction)" (YouTube; locked camera, phone stopwatch in
  shot), shown at 0.6x and 0.25x. Montage: Kont Kont (dye in hot, warm, cold water) and Science Explained (a ring of
  clock reactions). Aymen takes responsibility for the YouTube rights; every source is credited on the end card.
- **What is real:** the beaker outlines are SAM 3.1's own, from Argus's `segment()` on the exact frames shown (2 calls,
  $0.005, logged in `data/film/model-calls.jsonl`); the times 12.5, 13.6, 13.7, 13.8 s are read off the clip's stopwatch,
  frame by frame (never by a model); the app screens are captures of the live demo. The plan, notes, chat, verdict and
  next-run numbers are a concept illustration with simple values, labelled on screen.
- **Sound:** narration by ElevenLabs Eleven v4, voice "Christopher" (D-99), every line word-checked by a transcriber;
  an instrumental bed from ElevenLabs Music entering when the beaker turns black; 39 small sounds on visible actions
  (the video kit's and HyperFrames' bundled ones). Voice at −16 LUFS, music about 15 LU under it.

### Version 2 (Nov 4, D-101)

2:52, "accelerating research": researchers told Aymen they stand for hours watching experiments. Order: lab footage and
"what slows research down" → 24 hours of real E. coli swarms (Shaw et al. 2026, CC BY 4.0) → Argus title → overnight:
SAM 3.1's outlines from Argus's own run on every scan, the measured areas counting up, a morning chart of the real
curves (2,658 / 2,653 / 2,499 mm² at 24 h; detection gaps dropped, D-90) → the graded clock-reaction story (plan,
watch, checked notes, Ask Argus, verdict, next run) → the real app's dye and seed runs → microscope mode as "next"
(not built) → under the hood → "24 h of watching → 2 min of reading" → the demo link. Credits: DIY bama and Heidi
Arjes (YouTube), Kindel Media and Dominik Zítka (Pexels), Shaw et al. 2026, ElevenLabs voice and music.

Version 3 (D-102, 2:56) swaps the clock-reaction clip for BeardedScienceGuy's two glasses (two strengths, poured
together; B 1.4 s, A 5.3 s after the pour, measured from the frames) and retells that part as "does the strength
change when it turns black?". Credits: BeardedScienceGuy and Heidi Arjes (YouTube), Kindel Media and Dominik Zítka
(Pexels), Shaw et al. 2026 (CC BY 4.0), ElevenLabs.

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
