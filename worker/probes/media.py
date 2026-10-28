"""Probe short-clip input on Muse Spark 1.3 and Muse Voice Transcribe.

Clip: probes/out/pan.mp4 from probes.sam (6 s, 240x240, 10 fps), plus a 12 s loop of it, to see
how video tokens scale with duration. Voice: a Windows text-to-speech recording of a short
researcher note (synthetic speech, used only to check the request shape and latency).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any

import requests

from ._common import OUT, client, file_data_url, load_prompt, save, usage_row

SPARK = os.environ["REASONING_ROUTINE_MODEL"]


def probe_clip_tokens() -> list[dict[str, Any]]:
    short = OUT / "pan.mp4"
    long = OUT / "pan_12s.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "1", "-i", str(short), "-c", "copy", str(long)],
        check=True,
    )
    rows = []
    for clip, seconds in ((short, 6), (long, 12)):
        started = time.perf_counter()
        response = client().responses.create(
            model=SPARK,
            instructions=load_prompt("system/scientific-rules.md"),
            input=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "In one sentence: what moves in this clip?"},
                        {"type": "input_video", "video_url": file_data_url(clip, "video/mp4")},
                    ],
                }
            ],
            reasoning={"effort": "minimal"},
            max_output_tokens=800,
        )
        row = usage_row(SPARK, response.usage, time.perf_counter() - started)
        rows.append({"clip_seconds": seconds, "clip_px": "240x240", "fps": 10, **row, "text": response.output_text})
    return rows


def probe_voice() -> dict[str, Any]:
    audio = OUT / "voice_24k.wav"
    request = {"model": os.environ["VOICE_MODEL"], "audioEncoding": "WAV"}
    started = time.perf_counter()
    response = requests.post(
        f"{os.environ['META_BASE_URL']}/asr/transcribe",
        headers={"Authorization": f"Bearer {os.environ['MODEL_API_KEY']}"},
        files={
            "request": (None, json.dumps(request), "application/json"),
            "audio": (audio.name, audio.read_bytes(), "audio/wav"),
        },
        timeout=60,
    )
    latency = time.perf_counter() - started
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
    return {
        "status_code": response.status_code,
        "latency_s": round(latency, 2),
        "audio_bytes": audio.stat().st_size,
        "response": body,
    }


def main() -> None:
    save("media_clip_tokens", probe_clip_tokens())
    save("media_voice", probe_voice())


if __name__ == "__main__":
    main()
