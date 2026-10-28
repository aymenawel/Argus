# 12 · Skills: for building (Claude Code) and for Argus itself (runtime)

## Installed for Claude Code: `.claude/skills/`

Seven skills, copied unchanged from pinned commits and checked before install (no network calls, no shell commands, no credential access). Licenses and pinned commits: `THIRD_PARTY_NOTICES.md`.

| Skill | From | Use it when building… |
| --- | --- | --- |
| `experimental-design` | K-Dense-AI/scientific-agent-skills (MIT) | DOE planner, randomization, blocking (`scripts/doe_designs.py`, `scripts/randomization.py`) |
| `statistical-power` | same | Replicate calculator (`scripts/power.py` wraps statsmodels) |
| `uncertainty-and-units` | same | ± propagation, rounding rules, unit checks |
| `hypothesis-generation` | same | Hypothesis builder, rival explanations, pre-registration fields |
| `scientific-critical-thinking` | same | Verdict critique, bias/confounding checks |
| `opencv` | tondevrel/scientific-agent-skills (MIT) | Camera capture, video, contours, drawing |
| `trackpy-particle-tracking` | jaechang-hits/SciAgent-Skills (CC BY 4.0) | Microscope particle tracking (later) |

Notes:
- `scientific-critical-thinking` mentions optional figure generation through another skill that sends prompts to OpenRouter. That skill is **not installed**, so nothing is sent anywhere.
- Earlier I suggested SciAgent's `opencv-bioimage-analysis`; I installed tondevrel's `opencv` instead because it focuses on camera and video work (Argus's core), not fluorescence microscopy.
- Neither OpenCV skill covers Argus-specific needs (locking exposure, ArUco, SSIM keyframes). Those are in `03-watcher-design.md` and `09-measurement-and-calibration.md`.
- Add more skills only after reading their `SKILL.md` and scanning their scripts.

## How Argus uses the science skills at runtime [decided]

Argus's own AI (Muse Spark / Wonder) does **not** load skills. Three pieces replace them:

1. **Short rules (~350 tokens), cached:** `prompts/system/scientific-rules.md`, distilled from hypothesis-generation and scientific-critical-thinking. Sent first on every reasoning call so prompt caching applies.
2. **Math as Python functions:** experimental-design, statistical-power, uncertainty-and-units and statistical analysis become worker code (tools the AI can call). Matches the rule that the model never computes numbers.
3. **Deep-tier critique only when needed:** `prompts/deep/verdict-critique.md` (fuller checklist) runs on Muse Wonder for verdicts, next-run suggestions and the final report: a few times per run.

**Method cards** (`prompts/recipes/<recipe>/method.md`): a short card per recipe (what to measure, the typical curve, recipe-specific rival explanations), loaded only when that recipe runs. Same "load only what's needed" idea as skills, sized for Argus.

**Why not load full skills:** the 7 relevant skills are ~15,700 words (~21,000 tokens). On 3,000 Spark calls that's ~$78 extra, over half the $150 credit, and long instructions make answers less focused.

## Other skill sources reviewed

| Repo | Verdict |
| --- | --- |
| K-Dense-AI/scientific-agent-skills (177 skills, MIT) | Best for reasoning, design and statistics |
| jaechang-hits/SciAgent-Skills (CC BY 4.0) | Best reference for image-analysis recipes: Cellpose, scikit-image, OpenCV bio-imaging, western blots, napari |
| tondevrel/scientific-agent-skills (MIT) | OpenCV, scikit-image, scikit-video, photutils |

Useful later from these repos: `cellpose-cell-segmentation`, `scikit-image-processing`, `western-blot-quantification`, `openpiv`, `timesfm-forecasting` (time-to-target forecasts), `protocolsio-integration` (import a published protocol into the brief), `pylabrobot`, `opentrons-integration`, `labarchive-integration`.
