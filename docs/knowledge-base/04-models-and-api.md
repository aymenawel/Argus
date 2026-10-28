# 04 · Models and the Meta Model API

> Verified against dev.meta.ai docs on **Oct 27, 2026**. If a call fails, re-check the linked page first; APIs change.

## Connection

| Item | Value |
| --- | --- |
| Base URL | `https://api.meta.ai/v1` |
| Auth | API key in env var **`MODEL_API_KEY`** (the OpenAI SDK won't read it automatically; pass it explicitly) |
| SDK | OpenAI SDK (`pip install openai`, `npm install openai`) |
| Protocol used in Meta's docs | **Responses API** (`client.responses.create`). Chat Completions and a Messages API also exist |
| Docs | https://dev.meta.ai/docs/overview |

```python
import os
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
r = client.responses.create(model="muse-spark-1.3", input="ping")
print(r.output_text, r.usage)
```

## Models Argus uses

| Role | Model ID | Input | Notes |
| --- | --- | --- | --- |
| Routine reasoning (notes, checkpoints) | `muse-spark-1.3` | text, image, video, audio, PDF; 1,048,576-token context | Audio input "not fully supported" on 1.3 (Meta suggests 1.2 for audio); Argus uses Voice Transcribe for audio anyway |
| Deep reasoning (verdicts, critique, next-run explanation, report) | `muse-wonder-1.0` (Preview) | text, **image**, video, audio, PDF; 1,048,576 tokens | Image input confirmed on the models page. Standard tier only |
| Segmentation | `sam-3.1` | text prompt, image, video → boxes + masks | One concept per request |
| Voice notes | `muse-voice-transcribe-1.0` | audio → transcript | 25 languages |
| Cheaper testing (optional) | `muse-spark-1.3-contributor` | same as 1.3 | Meta uses your content for training; 150 RPM limit; no `max` effort |

Not on the Model API: **Muse Spark Open** (~816B params; hosted providers such as Baseten `meta-models/muse-spark-open-1026`) and **Muse Glimmer** (30B, Apache 2.0, self-host or Fireworks/Together/OpenRouter/Ollama). **Muse Wonder Full** is Muse Code subscription only.

## Optional: Muse Spark Open on Baseten for the $10K open-weight bonus [kept as an option, D-33]

Not used for now (no partner credits; it would be paid by card). Switching the routine tier is one config change if Aymen decides to go for the bonus later.

The "Best Build on Meta Open Weight Models" prize requires Muse Glimmer or Muse Spark Open "served on participants' own hardware or through partner-provided inference," verified by the infrastructure partner. Baseten is a hackathon partner.

| Item | Value |
| --- | --- |
| Base URL | `https://inference.baseten.co/v1` (OpenAI-compatible) |
| Auth | `BASETEN_API_KEY`, sent as `Authorization: Bearer ...` |
| Model | **`meta-models/muse-spark-open-1026`** (hackathon name; Baseten's docs show `meta-models/muse-spark-open`) |
| Protocol | **Chat Completions** (`client.chat.completions.create`) |
| Images | `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,...", "detail": "auto"}}`; `detail` = `auto`, `low` (512 px max) or `high` |
| Price | $1.25 in / $4.25 out per 1M tokens per a third-party price tracker (same as Muse Spark 1.3); confirm on Baseten. $100 credit if the application is approved (Q-03) |
| Context | 1,048,576 tokens; vision supported |

Glimmer alternative: Fireworks lists `accounts/fireworks/models/muse-glimmer-30b` (image input, 131k context) but says it is being deprecated on **serverless** starting Sep 25, 2026, leaving paid on-demand deployments. Not worth it for this build. Self-hosting Glimmer on Modal is possible but costs setup time.

**One code path for both providers:** Meta's API also supports Chat Completions, so `reason()` uses Chat Completions for every provider (structured output there uses `response_format` with a JSON schema; verify on day one). SAM 3.1 stays on Meta's Responses API inside `segment()`.

## Images to a reasoning model

```python
import base64
b64 = base64.b64encode(open("snap.jpg", "rb").read()).decode()
r = client.responses.create(
    model="muse-spark-1.3",
    input=[{"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": "..."},
        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
    ]}],
)
```

- Max 50 images per request; 50 MB per inline image; JPEG/PNG/GIF/WebP.
- **Image tokens scale with resolution:** ~1,300–1,500 tokens for a ~1280 px image. Downscale snapshots (e.g. 768 px long side) to cut cost.
- Exact count before sending: `POST /v1/responses/input_tokens` with the same `input`.

## Video to a reasoning model (short clip mode)

`{"type": "input_video", "video_url": "<public URL or base64 data URL>"}` or upload with the Files API (`purpose="user_data"`) and pass `{"type": "input_file", "file_id": "..."}`. **MP4 only.** Token cost of video isn't documented: measure it on day one.

## Structured output (every AI note)

```python
r = client.responses.create(
    model="muse-spark-1.3",
    input=[...],
    text={"format": {"type": "json_schema", "name": "ArgusNote",
                     "schema": NOTE_SCHEMA, "strict": True}},
)
```

- Parameter is **`text.format`** (not `response_format`) on the Responses API.
- `strict: true` requires `additionalProperties: false` and every key in `required`. No recursive schemas. Schemas live in `prompts/schemas/`.
- The structured-output page shows no Responses code sample; the shape above follows its parameter description. Test it on day one.

## Reasoning effort

`reasoning={"effort": "low"}` on the Responses API. Values: `minimal`, `low`, `medium`, `high`, `xhigh`, `max` (`none` returns HTTP 400 on Muse models; `max` not on contributor). Reasoning tokens are **billed as output tokens** and count toward `max_output_tokens`. Suggested: `low` for routine notes, `high` for deep calls; tune with real costs.

## Prompt caching

Automatic, no flags. Put stable content first (rules → method card → locked plan → summary → new data). Optional `prompt_cache_retention="24h"` (a hint). Check hits in `usage.input_tokens_details.cached_tokens`.

## SAM 3.1

Request (image):

```json
{"model": "sam-3.1", "stream": true,
 "input": [{"type": "message", "role": "user", "content": [
   {"type": "input_text", "text": "seed"},
   {"type": "input_image", "image_url": "data:image/jpeg;base64,..."}]}],
 "metadata": {"mask_encoding": "one_bit", "include_confidence": "true"}}
```

- **One concept per request.** Comma or "+" lists return zero matches. Every matching instance is returned.
- Box/point prompts use a token grammar, e.g. `<0f>1<|box;x1=..;y1=..;x2=..;y2=..;w=W;h=H|>`; up to 16 objects; `w`/`h` must match the media's pixel size.
- `mask_encoding`: `lossless` (default) or `one_bit` (several times smaller). Box/point prompts always return `one_bit`.
- **Video:** `input_video` with `video_url` or `file_id`; MP4/MOV with H.264, H.265 or MPEG-4 (no VP9/WebM); up to **15,000 frames (~10 min) per request**; up to 16 tracked objects; **billed at least 50 frames per request**. `metadata.propagation_direction`: `both` | `forward` | `backward`.
- With concept prompts, the leading integer per record is an object ordinal; the docs don't promise it stays the same across frames, so Argus matches IDs itself in image mode.
- **Parsing:** output is a custom text grammar streamed in the Responses output-text lane. Use the official **`meta-sam-parser`** (`pip install meta-sam-parser`; Python ≥3.10, no dependencies): `decode_mask_to_raster`, `decode_mask_to_rle`, `build_object_prompt`. Writing your own parser is possible but not worth the time.
- Docs: https://dev.meta.ai/docs/sam/segmenting · https://dev.meta.ai/docs/sam/reading-segmentation · https://dev.meta.ai/docs/sam/client-libraries

## Voice notes

`POST https://api.meta.ai/v1/asr/transcribe` (multipart: `request` JSON + `audio` WAV), header `Authorization: Bearer $MODEL_API_KEY`. Audio must be **WAV, mono, 16-bit PCM, 16 or 24 kHz**, ≤10 min, ≤32 MB. Convert with `ffmpeg -i in.m4a -ac 1 -ar 24000 -c:a pcm_s16le out.wav`. Response JSON has `transcript` and `turns`. Docs: https://dev.meta.ai/docs/speech-to-text

## Rate limits (per team, per model)

| Model | RPM | TPM |
| --- | --- | --- |
| `muse-spark-1.3` | 3,000 | 4,000,000 |
| `muse-wonder-1.0` | 3,000 | 4,000,000 |
| `muse-spark-1.3-contributor` | 150 | 3,000,000 |
| `sam-3.1` | 3,000 | none |
| `muse-voice-transcribe-1.0` | 256 concurrent streams | none |

## Cookbook pointers (github.com/meta-models/meta-model-cookbook, MIT)

`01_api_fundamentals` (vision input, structured output, prompt caching, reasoning tokens, error handling/retry), `02_agent_patterns` (perceive-decide-act loop, alert-fatigue copilot), `06_muse_voice`, `07_sam` (image and video segmentation basics).

## Day-one API checks (do these before building on them)

- [ ] One `muse-spark-1.3` call with 2 snapshots → read `usage` (input, cached, output tokens)
- [ ] Same with `muse-wonder-1.0` (confirm image input works for you)
- [ ] One strict JSON-schema call with `prompts/schemas/note.json`
- [ ] One SAM 3.1 image call on a real frame, parsed with `meta-sam-parser`
- [ ] One short MP4 to SAM video and to Muse Spark (token/frame cost)
- [ ] One voice note through `/v1/asr/transcribe`
