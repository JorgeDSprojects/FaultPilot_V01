from pathlib import Path

from faultpilot.retrieval.config import load_settings


def test_load_settings_has_rrf_keys() -> None:
    settings = load_settings(Path("config/settings.yaml"))

    assert settings.retrieval.rrf_k == 60
    assert settings.retrieval.final_k == 8


def test_route_profile_override_alarm_lookup() -> None:
    settings = load_settings(Path("config/settings.yaml"))
    profile = settings.retrieval.profile_for_route("alarm_lookup")

    assert profile.bm25_k == 60
    assert profile.dense_k == 20
