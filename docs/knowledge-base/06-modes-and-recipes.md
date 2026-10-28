# 06 · Analysis modes, experiment modes and recipes

## Analysis modes (how often the AI looks) [decided]

| Mode | How it works | Best for |
| --- | --- | --- |
| **Continuous** | Fixed rhythm (every 2–10 s), whether or not anything changed | Short, fast runs: reactions, dissolving, melting, live demos |
| **Smart trigger** | Local watcher compares frames; SAM runs only on change; reasoning runs when a measurement crosses a threshold. Scheduled check-in catches drift; cooldown stops repeats | Long, mostly stable runs: plants, crystals, fermentation over days |
| **Hybrid** | Continuous during the active phase, drops to Smart trigger when things settle, flips back on a burst of change | Fast start, long tail |

- Smart trigger is **an option, never forced**: short experiments with constant change would be hurt by it.
- Wizard suggestion by duration: under 1 hour → Continuous; days → Smart trigger; unsure → Hybrid. The researcher can override and **switch mid-experiment**.
- Interval, sensitivity, check-in timing and cooldown are all adjustable.

## Experiment modes become recipes [decided]

The original fixed modes become **starter recipes** on one shared pipeline:

| Starter | Input | Tracks | Extras |
| --- | --- | --- | --- |
| General | Webcam or phone | Whatever the researcher describes ("liquid level in the jar") | Base for all others |
| Plant (GrowLoop) | Webcam, timelapse | Leaf area, height, greenness, droop, new growth | Smart-plug light/pump control with limits and optional approval; day/night aware |
| Microscope | USB microscope | Particle/crystal/cell count and size over time | Calibration slide → µm |
| Reaction | Webcam | Color change, bubbling, precipitate, level | Defaults to Continuous |
| Custom | Any camera | Researcher-chosen metrics and triggers | Full control |

A researcher can also describe a new experiment in plain words; the AI drafts a recipe for them to review (later feature).

## Recipe format [proposed]

```yaml
# recipes/seed-germination.yaml
id: seed-germination
version: 1
title: Seed germination
default_mode: smart_trigger
segment:
  - concept: seed            # one SAM concept per request
  - concept: root
measurements:
  - {metric: germinated_count, from: root, rule: "root length > 2 mm", unit: count}
  - {metric: root_length, from: root, method: skeleton_length, unit: mm}
curve: cumulative_germination   # fit → T50 (time to 50%), max %, rate
events:
  - {name: first_germination, when: "germinated_count >= 1"}
  - {name: half_germinated, when: "germinated_fraction >= 0.5"}
watcher: {signals: [ssim, color], light_normalization: strong, day_night: true}
rival_explanations: [temperature, uneven_watering, position_in_tray, seed_batch]
method_card: prompts/recipes/seed-germination/method.md
```

## The five measurement families

Every recipe mixes these; that is why one engine covers many fields.

| Family | What Argus computes | Typical result |
| --- | --- | --- |
| Size and shape | Area, height, length, diameter, angle, roundness (mm after calibration) | Growth curve, rate per hour, final size |
| Color and intensity | Mean color in a lighting-corrected space, color difference from start, brightness, cloudiness | Reaction rate, endpoint time, concentration via standard curve |
| Count | Number of objects and when each appeared | Percent done over time, time to 50% |
| Motion | Position, speed, path, time in zone, flow field | Velocity, acceleration, fitted constants |
| State and events | First appearance, phase change, overflow, contamination, "nothing changing" | Onset time, alerts, checkpoints |

## Experiment catalog (what researchers run that Argus can measure)

| Field | Experiment | What Argus measures | Tool to borrow from |
| --- | --- | --- | --- |
| Plants | Seed germination under treatments | Germinated over time, T50, root length | SeedGerm (method), PlantCV |
| Plants | Growth under light/water/fertilizer | Leaf area, height, greenness, growth rate | PlantCV |
| Plants | Phototropism / gravitropism | Stem bending angle over time | SAM mask + skeleton |
| Microbiology | Colony growth on agar | Count, appearance time, colony size | OpenCFU (method) |
| Microbiology | Antibiotic/antiseptic disk test | Clear-zone diameter (mm), how fast it forms | OpenCV circle fitting |
| Fermentation | Yeast foam, dough rise, kombucha | Height, max rise rate | Argus Card for mm |
| Microbiology | Liquid culture cloudiness | Cloudiness as growth proxy, lag, max rate | Standard curve vs known dilutions |
| Cell biology (microscope) | Scratch / wound-healing assay | Gap area closed, lag, repair rate | KREAP (Gompertz fit) |
| Cell biology (microscope) | Cell counts and motility | Count, track speed, direction | Cellpose, trackpy |
| Chemistry | Color-change kinetics (iodine clock, indicator fading, dye bleaching) | Color difference over time, endpoint, rate constant | Smartphone colorimetry methods |
| Chemistry | Precipitation and crystallization | Cloudiness onset, crystal count/size, growth rate | Webcam crystal monitoring (literature) |
| Chemistry | Gas-producing reactions (catalase + peroxide foam, balloon) | Foam height or balloon diameter, rate | Size family |
| Chemistry | Corrosion, rusting, electroplating | Rusted/coated area %, color change | Color + area |
| Materials | Drying, curing, evaporation, melting | Droplet/ice area, contact line, time to dry/melt | Size + state |
| Materials | Coating, paint, plastic aging (heat, light, humidity) | Discolored/peeled area %, crack count/length, onset | Color + size, crack masks |
| Materials | Cracking while drying/curing (clay, cornstarch, plaster, gels) | First crack time, total crack length, pattern, shrinkage | Skeleton analysis |
| Chemistry | Phase separation and settling (emulsions, suspensions) | Height of each layer, separation rate, layer cloudiness | Size + color per layer |
| Energy | Long battery tests (outside of the cell only) | Visible swelling/leakage, linked to voltage/temperature logs | Log import. **Never** replaces battery safety systems |
| Food science | Fruit browning, mold on bread, spoilage | Browning index, mold area %, onset day | Color + count |
| Physics | Pendulum, falling object, projectile, spring | Position, speed, acceleration, fitted g or damping | Tracker (method) |
| Physics | Convection, mixing, dye diffusion | Flow velocity field, mixing index, front speed | OpenPIV (GPL) |
| Animal behavior | Daphnia, brine shrimp, ants, flies, worms, small fish | Speed, distance, time in zone, response to light/chemicals | ToxTrac, idtracker.ai, trackpy |
| Biology | Slime mold growth and maze solving | Area, network length, front speed | Skeleton analysis |
| Molecular biology | Gel electrophoresis / blot images | Band position and intensity | western-blot-quantification skill |
| Environment | pH strips, water test strips | Value read from the color chart | Color + calibration |

Camera-invisible quantities (temperature, mass, pH without indicator) need sensors; see `10-hardware-and-control.md`.

## First recipes for the demo [decided direction]

Pick 2–3 that are fast or already recorded: a **color-change reaction** (fast, live), **foam or growth height** (size family), and **seed germination** (multi-day, record raw footage from day one).
