from pathlib import Path

import pytest
from pydantic import ValidationError

from argus.config import REPO_ROOT, load_settings


def test_defaults_when_env_is_empty():
    s = load_settings({})
    assert s.routine_model == "muse-spark-1.3" and s.deep_model == "muse-wonder-1.0"
    assert s.deep_fallback_model == "muse-spark-1.3" and s.run_spend_cap_usd == 10.0
    assert s.data_dir == REPO_ROOT / "data" and s.recipes_dir == REPO_ROOT / "recipes"
    assert s.model_api_key is None


def test_env_overrides_and_key_is_hidden():
    s = load_settings({"MODEL_API_KEY": "k" * 48, "RUN_SPEND_CAP_USD": "2.5", "ARGUS_DATA_DIR": "C:/tmp/argus data"})
    assert s.run_spend_cap_usd == 2.5 and s.data_dir == Path("C:/tmp/argus data")
    assert "k" * 48 not in repr(s) and s.model_api_key.get_secret_value() == "k" * 48


@pytest.mark.parametrize("bad", ["abc", "0", "-1"])
def test_invalid_spend_cap_is_rejected(bad):
    with pytest.raises(ValidationError):
        load_settings({"RUN_SPEND_CAP_USD": bad})


def test_sam_timeout_is_read_from_the_environment():
    assert load_settings({"SAM_TIMEOUT_S": "45"}).sam_timeout_s == 45.0


def test_reasoning_defaults_follow_kb_04_and_05():
    s = load_settings({})
    assert (s.routine_effort, s.routine_max_output, s.deep_effort, s.deep_max_output) == (
        "minimal",
        4000,
        "medium",
        8000,
    )
    assert (s.spark_input_usd, s.spark_cached_usd, s.spark_output_usd) == (1.25, 0.15, 4.25)
    assert (s.wonder_input_usd, s.wonder_cached_usd, s.wonder_output_usd) == (4.00, 0.20, 20.00)
    assert s.fallback_effort == "high" and s.snapshot_px == 768 and s.reason_concurrency == 2


def test_the_open_model_settings_are_read_from_the_environment():
    settings = load_settings(
        {
            "REASONING_ROUTINE_PROVIDER": "baseten",
            "BASETEN_API_KEY": "secret",
            "BASETEN_BASE_URL": "https://example.org/v1",
            "REASONING_OPEN_MODEL": "meta-models/muse-spark-open",
        }
    )
    assert settings.routine_provider == "baseten" and settings.open_model == "meta-models/muse-spark-open"
    assert settings.baseten_api_key.get_secret_value() == "secret" and "secret" not in repr(settings)
    assert settings.baseten_base_url == "https://example.org/v1"
    assert load_settings({}).open_model == "meta-models/muse-spark-open-1026"
