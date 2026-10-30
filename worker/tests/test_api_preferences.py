"""The app's switch for where everyday model calls run (D-77): Meta's API (Muse Spark 1.3) or Muse Spark Open on
Baseten. Saved in the database, so it survives a restart; verdicts and SAM never move."""

from argus.config import load_settings
from argus.preferences import active_provider
from tests.api_client import api_client

BOTH_KEYS = {"MODEL_API_KEY": "meta-key", "BASETEN_API_KEY": "baseten-key"}


def test_the_switch_starts_on_meta_and_lists_both_providers(db, tmp_path):
    with api_client(db, tmp_path, env=BOTH_KEYS) as client:
        answer = client.get("/api/preferences/reasoning").json()
    assert answer["provider"] == "meta"
    options = {o["id"]: o for o in answer["options"]}
    assert options["meta"]["model"] == "muse-spark-1.3" and options["meta"]["available"] is True
    assert options["baseten"]["model"] == "meta-models/muse-spark-open-1026" and options["baseten"]["available"]
    assert answer["fixed"] == {"verdicts": "muse-wonder-1.0", "segmentation": "sam-3.1"}
    assert "baseten-key" not in str(answer) and "meta-key" not in str(answer)


def test_switching_to_baseten_is_saved_and_survives_a_restart(db, tmp_path):
    with api_client(db, tmp_path, env=BOTH_KEYS) as client:
        assert client.put("/api/preferences/reasoning", json={"provider": "baseten"}).json()["provider"] == "baseten"
    with api_client(db, tmp_path, env=BOTH_KEYS) as client:
        assert client.get("/api/preferences/reasoning").json()["provider"] == "baseten"
        assert client.put("/api/preferences/reasoning", json={"provider": "meta"}).json()["provider"] == "meta"
    assert active_provider(db, load_settings(BOTH_KEYS)) == "meta"


def test_baseten_needs_its_key_and_unknown_providers_are_refused(db, tmp_path):
    with api_client(db, tmp_path, env={"MODEL_API_KEY": "meta-key"}) as client:
        refused = client.put("/api/preferences/reasoning", json={"provider": "baseten"})
        assert refused.status_code == 422 and "BASETEN_API_KEY" in refused.json()["detail"]
        assert client.put("/api/preferences/reasoning", json={"provider": "elsewhere"}).status_code == 422
        assert client.get("/api/preferences/reasoning").json()["provider"] == "meta"


def test_a_saved_baseten_choice_without_its_key_runs_on_meta(db, tmp_path):
    with api_client(db, tmp_path, env=BOTH_KEYS) as client:
        client.put("/api/preferences/reasoning", json={"provider": "baseten"})
    assert active_provider(db, load_settings({"MODEL_API_KEY": "meta-key"})) == "meta"
