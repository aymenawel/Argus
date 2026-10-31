# Argus

**An AI lab partner that watches your experiments, measures what changes in real units, judges your hypothesis
and suggests the next run.** Point a webcam or USB microscope at the bench; Argus does the rest of the loop:

```
Plan  →  Watch  →  Measure  →  Judge  →  Next run
```

**Everything shown was built Oct 27 – Nov 4, 2026**, solo, for the Meta Global AI Developer Hackathon (Indie track).

## See it without installing anything

**Public replay: [argus-replay.vercel.app](https://argus-replay.vercel.app)**. Finished runs, recorded and replayed
read-only in the same app: the Run view (frames with SAM's outlines, readings, notes, the timeline, the verdict) and
Results (fitted curves, half-way times, the verdict's checks, the next run, the videos). Nothing on it is live, and
every page says so. The germination plate is published data (Genze et al. 2020, CC BY 4.0), credited on every page.

## How it works

- **Watch.** A cheap local watcher reads every frame and wakes the expensive steps only when something changed.
- **Measure.** SAM 3.1 outlines each vessel's contents; code turns outlines and colours into readings in real units
  (mm, mm², ΔE00, counts), each with its ± from the scale card or the dish rim. The model never computes a number.
- **Notes.** Muse Spark writes what happened, but every number in a note is a reference to a stored reading, and a
  claim checker rejects any note with a number of its own or a claim beyond what the data allows.
- **Judge.** Code decides which verdicts the data allows (supported, not supported, inconclusive, too early) from the
  plan locked before the run; Muse Wonder explains the verdict, names rival explanations, and a critique checks it.
- **Next run.** Code sizes the next run (vessels per condition, run length) from this run's spread and fitted curves,
  Ax proposes levels to try, and Muse Wonder explains why. A suggestion: Argus never starts a run by itself.

Observations, measurements, AI notes and the researcher's reviews are separate records; nothing overwrites evidence.

## Meta models, and where each is used

| Model | Used for |
| --- | --- |
| **SAM 3.1** (`sam-3.1`) | Segmentation: finding and outlining vessels and what is in them, frame by frame |
| **Muse Spark 1.3** (`muse-spark-1.3`) | Routine notes at events and checkpoints; drafting a recipe and plan from the researcher's own words |
| **Muse Wonder 1.0** (`muse-wonder-1.0`) | The verdict, its critique, and the reasons for the next run |
| **Muse Spark Open** on Baseten (`meta-models/muse-spark-open-1026`) | The routine tier on open weights, switchable in Settings; falls back to Muse Spark 1.3 |

Every model call is logged with its model, tier, tokens, cost and latency, and a spend cap stops calls per run.

## Run it

You need [uv](https://docs.astral.sh/uv/), Node.js 24, and [ffmpeg](https://ffmpeg.org/) on your PATH.

```bash
cp .env.example .env            # add MODEL_API_KEY (Meta Model API); BASETEN_API_KEY is optional
cd worker && uv sync && cd ../web && npm ci && cd ..
cd worker && uv run python -m argus dev
```

The worker runs on http://localhost:8000 and the app on http://localhost:3000. Without a key, Argus still watches
and measures, and code writes the next run's reasons; notes, verdicts and recipe drafts are off.

### Videos, the replay and the validation table

From `worker/`, for a finished run:

```bash
uv run python -m argus media timelapse RUN_ID   # the whole run in 20 s, its curves drawn over it (1080p)
uv run python -m argus media reel RUN_ID        # 30–60 s of the moments that mattered
uv run python -m argus export-bundle RUN_ID     # the run as a bundle for the public replay (web/public/bundles)
uv run python -m argus validation --runs RUN_ID # the table below
```

The Videos card on Results makes the same videos. `web/scripts/deploy-replay.sh` deploys the replay to Vercel.
Videos and bundles are made from stored records only: no model is called and nothing is recomputed.

## Validation

How well Argus measured, printed by `uv run python -m argus validation --runs run_9334d302e075` from the database,
pasted unedited. A check with nothing stored behind it says "not measured yet".

| Check | Run | Result |
|---|---|---|
| Scale | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | dish rims at the dataset's stated 85 mm diameter · 0.145 ± 0.007 mm/px |
| Noise floor | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | germinated_count: 0 count (still period) |
| Noise floor | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | seed_area: 4.1 mm2 (still period) |
| Counting against labels | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | germinated_count: mean absolute error 1.50 count, exact on 35% of 564 frames |
| Events caught | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | not measured yet |
| Claim checker | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | 1 accepted first try, 2 after a retry, 1 written by code; 4 answers rejected: quantity in words ×7 |
| Models | Rye vs pearl millet (Genze plate, speed) (run_9334d302e075) | SAM 95 of 95 calls succeeded · spend $0.71 |

SAM 3.1 returns at most 16 objects per request, so a dish with more seeds and sprouts than that can be undercounted;
the run flags it as a quality event at its first frame.

## Safety

- Argus watches and suggests; it controls no hardware.
- Plans and suggestions are screened: anything with flame, strong heat, pressure, hazardous chemicals or pathogens
  gets a safety warning and no automatic action.
- Argus gives no medical advice.

## Licence

Argus's own code is under the [MIT licence](LICENSE). Third-party skills, adapted prompts, the Inter typeface used in
the videos and the published data re-analysed in the demo keep their own licences: see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
