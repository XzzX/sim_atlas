import pytest

from sim_atlas_toolkit.settings import ToolkitSettings


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_ATLAS_LLM_ENABLED", "true")
    monkeypatch.setenv("SIM_ATLAS_LLM_URL", "http://env-llm")
    monkeypatch.setenv("SIM_ATLAS_LLM_MODEL", "env-model")
    monkeypatch.setenv("SIM_ATLAS_LLM_OVERWRITE", "true")

    settings = ToolkitSettings()

    assert settings.llm_enabled is True
    assert settings.llm_url == "http://env-llm"
    assert settings.llm_model == "env-model"
    assert settings.llm_overwrite is True
