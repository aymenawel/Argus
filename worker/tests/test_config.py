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
