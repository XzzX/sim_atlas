import pytest
from pydantic import ValidationError

from sim_atlas_toolkit.settings import ToolkitSettings


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_ATLAS_LLM_DOCSTRINGS", "overwrite")
    monkeypatch.setenv("SIM_ATLAS_LLM_URL", "http://env-llm")
    monkeypatch.setenv("SIM_ATLAS_LLM_MODEL", "env-model")

    settings = ToolkitSettings()

    assert settings.llm_docstrings == "overwrite"
    assert settings.llm_url == "http://env-llm"
    assert settings.llm_model == "env-model"


def test_llm_docstrings_defaults_to_no() -> None:
    assert ToolkitSettings().llm_docstrings == "no"


def test_llm_docstrings_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_ATLAS_LLM_DOCSTRINGS", "maybe")

    with pytest.raises(ValidationError):
        ToolkitSettings()


def test_embed_enabled_defaults_true() -> None:
    assert ToolkitSettings().embed_enabled is True


def test_embed_enabled_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIM_ATLAS_EMBED_ENABLED", "false")

    assert ToolkitSettings().embed_enabled is False
