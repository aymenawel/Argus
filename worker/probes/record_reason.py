"""Record one real Muse Spark note response as a test fixture for reason() (tests/test_reason.py).

Run by hand from worker/: `uv run --env-file ../.env python -m probes.record_reason` (about $0.006).
The saved file is the SDK response as JSON: check it holds no key or personal data before committing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ._common import client, load_prompt, load_schema

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "reason" / "note-response.json"

BLOCK = """MEASUREMENTS (cite only as {ref:<id>})
chg:C:delta_e | Glass C (warm), change since the start | 25.1 ± 0.1 dE00
chg:A:delta_e | Glass A (cold), change since the start | 2.2 ± 0.1 dE00
ev:1 | Dye added | 1:53"""

TASK = (
    "Write one checkpoint note about the run so far. Cite every number only as a {ref:<id>} token from the "
    "MEASUREMENTS block above; write no digits anywhere else. Put the ids you cite in numbers_used with value 0."
)


def main() -> None:
    response = client().responses.create(
        model=os.environ["REASONING_ROUTINE_MODEL"],
        input=[
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": load_prompt("system/scientific-rules.md")},
                    {"type": "input_text", "text": BLOCK},
                    {"type": "input_text", "text": TASK},
                ],
            }
        ],
        reasoning={"effort": "minimal"},
        max_output_tokens=4000,
        prompt_cache_key="argus:probe:routine:record",
        text={"format": {"type": "json_schema", "name": "ArgusNote", "schema": load_schema("note"), "strict": True}},
    )
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(response.model_dump(mode="json"), indent=1, ensure_ascii=False), encoding="utf-8")
    print(response.status, response.usage, FIXTURE)


if __name__ == "__main__":
    main()
