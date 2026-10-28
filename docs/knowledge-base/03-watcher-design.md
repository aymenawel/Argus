# 03 · Watcher design

> The watcher decides **when** to spend money on SAM and the reasoning model. It runs locally on every frame and is free. Plan decided after a brainstorm of 8 options.

## The two problems a naive watcher has

1. **Misses slow change.** Comparing each frame with the previous frame never triggers on a plant growing 0.1% per frame, even after 30% growth.
2. **Fooled by lighting.** Clouds, a lamp, or auto-exposure look like big changes.

## Build this (day 1–2) [decided]

1. **ROI from SAM at setup.** SAM finds each vessel once; the watcher looks only inside those regions (shadows, people and background are ignored).
2. **Light normalization.** Lock exposure and white balance where the camera allows (see `09-measurement-and-calibration.md`), then normalize brightness before comparing. For day/night plant runs, compare with a reference from the same lighting phase.
3. **Keyframe comparison.** Compare each frame with the **last frame that was analyzed**, not the previous frame, so slow drift accumulates until it crosses the threshold.
4. **Two cheap signals:** SSIM (`skimage.metrics.structural_similarity`) for shape/structure, and color statistics (mean and spread in a perceptual color space such as Lab) for color shifts. Trigger if either crosses its threshold.
5. **Debounce + cooldown + scheduled check-in.** A change must last a few frames; no re-trigger during cooldown; a forced check every N hours catches drift.

All OpenCV + scikit-image, CPU only.

## Upgrade once measurements exist [from the deep dive]

- **Trigger on the metric, not just pixels.** After the first SAM pass, track each vessel's metric (area, height, color) and trigger when it changes by a set amount. Pixel/SSIM stays as backup.
- **Adaptive pace.** Sample faster when change is quick or a predicted event is near; slower in flat stretches.
- **Phase detection.** Change-point detection (ruptures) marks lag / growth / plateau; boundaries become notes and chapters.

## Add only if testing shows false triggers

- **Embedding confirmation** with a small local model (`facebook/dinov2-small`, 22M params, Apache-2.0) to confirm a change is meaningful before calling SAM. Needs PyTorch (already pulled in by Ax).

## Skip [decided]

- **Background subtraction (MOG2/KNN):** absorbs slow change into the background, so plant growth never triggers. Opposite of what Argus needs.
- **Optical flow:** only helps motion-heavy reactions, which run in Continuous mode anyway.
- Perceptual hashing: too coarse.

## Per-recipe presets

| Recipe type | Signals | Notes |
| --- | --- | --- |
| Reaction / color change | Color stats (+ optional short clip) | Usually Continuous mode |
| Plant / germination | Keyframe SSIM + strong light normalization (+ embedding if needed) | Day/night aware |
| Microscope | SSIM + blob counting | Particles, crystals, cells |
| General | All signals, equal weight | Default |

## Frame-quality gate (runs before the watcher)

Blur score (variance of Laplacian), over/under-exposure check, and "object in the way" check. Bad frames are skipped and logged, not measured. A hand or tool entering the scene pauses measuring and logs a likely intervention, then the AI asks what happened.

## Pitch line

"Argus only spends AI on frames where something actually changed."
