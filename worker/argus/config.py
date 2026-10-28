"""Worker settings, read from the environment (the repo-root .env, loaded by uv or uvicorn).

Model IDs, base URLs and keys live here and nowhere else in the code (spec §7.1).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, PositiveFloat, SecretStr

REPO_ROOT = Path(__file__).resolve().parents[2]

# Environment variable → Settings field.
ENV_FIELDS = {
    "MODEL_API_KEY": "model_api_key",
    "META_BASE_URL": "meta_base_url",
    "REASONING_ROUTINE_MODEL": "routine_model",
    "REASONING_DEEP_MODEL": "deep_model",
    "REASONING_DEEP_FALLBACK_MODEL": "deep_fallback_model",
    "SEGMENT_MODEL": "segment_model",
    "VOICE_MODEL": "voice_model",
    "RUN_SPEND_CAP_USD": "run_spend_cap_usd",
    "ARGUS_DATA_DIR": "data_dir",
    "ARGUS_RECIPES_DIR": "recipes_dir",
    "ARGUS_WEB_ORIGIN": "web_origin",
}


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_api_key: SecretStr | None = None
    meta_base_url: str = "https://api.meta.ai/v1"
    routine_model: str = "muse-spark-1.3"
    deep_model: str = "muse-wonder-1.0"
    deep_fallback_model: str = "muse-spark-1.3"
    segment_model: str = "sam-3.1"
    voice_model: str = "muse-voice-transcribe-1.0"
    run_spend_cap_usd: PositiveFloat = 10.0
    data_dir: Path = REPO_ROOT / "data"
    recipes_dir: Path = REPO_ROOT / "recipes"
    web_origin: str = "http://localhost:3000"

    # SAM 3.1 prices and limits (KB 04 and 05, checked Oct 27, 2026); not read from the environment.
    sam_image_usd: float = 0.0025
    sam_video_frame_usd: float = 0.0002
    sam_video_min_frames: int = 50
    sam_max_objects: int = 16
    sam_max_video_frames: int = 15000
    sam_concurrency: int = 2
    sam_timeout_s: float = 120.0  # longest wait for the next bit of a SAM response; the SDK's own retries are off
    segment_interval_s: float = 10.0  # live runs: the shortest gap between two segmentations


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build settings from environment variables; unset or empty variables keep their defaults."""
    source = os.environ if env is None else env
    values = {field: source[name] for name, field in ENV_FIELDS.items() if source.get(name, "").strip()}
    return Settings(**values)
