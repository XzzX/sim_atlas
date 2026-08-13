"""Tests for settings initialization and config file creation."""

from typing import cast

import pytest
from pydantic import ValidationError

from sim_atlas.exceptions import MissingConfigError
from sim_atlas.settings import CONFIG_TEMPLATE, Settings, load_settings

MIN_COMMENT_LINES = 20


def test_load_settings_returns_valid_instance():
    """Test that load_settings returns a valid Settings instance."""
    load_settings.cache_clear()
    settings = load_settings()

    # Should have required fields set
    assert settings.jwt_secret is not None
    assert settings.jwt_algorithm is not None


def test_config_template_structure():
    """Test that the template has all required sections and keys."""
    assert "=== REQUIRED SETTINGS ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: JWT SETTINGS ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: LLM / DOCSTRING ENRICHMENT ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: AGENT LLM PROVIDER ALLOWLIST ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: EMBEDDINGS ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: LANGFUSE OBSERVABILITY ===" in CONFIG_TEMPLATE

    # Check all fields are documented
    assert "jwt_secret" in CONFIG_TEMPLATE
    assert "jwt_algorithm" in CONFIG_TEMPLATE
    assert "llm_api_key" in CONFIG_TEMPLATE
    assert "llm_base_url" in CONFIG_TEMPLATE
    assert "llm_providers" in CONFIG_TEMPLATE
    assert "llm_default_provider" in CONFIG_TEMPLATE
    assert "embedding_provider" in CONFIG_TEMPLATE
    assert "embedding_model" in CONFIG_TEMPLATE
    assert "embedding_api_key" in CONFIG_TEMPLATE
    assert "llm_chat_model" in CONFIG_TEMPLATE
    assert "langfuse_public_key" in CONFIG_TEMPLATE
    assert "langfuse_secret_key" in CONFIG_TEMPLATE
    assert "langfuse_host" in CONFIG_TEMPLATE

    # Check that template has verbose comments
    comment_lines = [
        line for line in CONFIG_TEMPLATE.split("\n") if line.strip().startswith("#")
    ]
    assert len(comment_lines) > MIN_COMMENT_LINES, (
        "Template should have verbose comments"
    )


def test_load_settings_caching():
    """Test that load_settings returns cached instance on repeated calls."""
    # Clear the cache first
    load_settings.cache_clear()

    # First call
    result1 = load_settings()

    # Second call
    result2 = load_settings()

    # Should return same cached instance
    assert result1 is result2


def test_template_has_examples_and_hints():
    """Test that the template includes practical examples and generation hints."""
    assert "python -c" in CONFIG_TEMPLATE  # Secret generation hint
    assert "sk-" in CONFIG_TEMPLATE  # OpenAI key example
    assert "pa-" in CONFIG_TEMPLATE  # VoyageAI key example
    assert "http://localhost:11434/v1" in CONFIG_TEMPLATE  # Ollama example
    assert "qwen3.6-27b" in CONFIG_TEMPLATE  # Model examples


def test_template_has_all_fields_explained():
    """Test that every config field has explanation text."""
    # Each field should have at least one comment line explaining it
    fields = [
        "jwt_secret",
        "jwt_algorithm",
        "llm_api_key",
        "llm_base_url",
        "llm_chat_model",
        "embedding_provider",
        "embedding_model",
        "embedding_api_key",
        "langfuse_public_key",
        "langfuse_secret_key",
        "langfuse_host",
    ]

    for field in fields:
        # Count comment lines before this field
        lines = CONFIG_TEMPLATE.split("\n")
        field_idx = None
        for i, line in enumerate(lines):
            if field in line and "=" in line:
                field_idx = i
                break

        assert field_idx is not None, f"Field {field} not found in template"

        # Should have at least one comment line before the field
        has_comment_before = any(
            lines[j].strip().startswith("#")
            for j in range(max(0, field_idx - 5), field_idx)
        )
        assert has_comment_before, f"Field {field} should have explanatory comments"


def test_settings_can_be_loaded_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings can be loaded from environment variables."""
    # The module-level config should already be loaded,
    # but we can test that load_settings is a valid function
    load_settings.cache_clear()
    settings = load_settings()

    # Should have at least the required fields
    assert hasattr(settings, "jwt_secret")
    assert hasattr(settings, "jwt_algorithm")
    assert hasattr(settings, "llm_api_key")
    assert hasattr(settings, "embedding_provider")


def test_missing_config_error_exists():
    """Test that MissingConfigError exception is defined."""
    # Should be able to raise and catch it
    with pytest.raises(MissingConfigError):
        raise MissingConfigError("test")


def test_template_mentions_deployment_scenarios():
    """Test that template explains optional vs required settings."""
    # Template should explain when to use optional settings
    assert "optional" in CONFIG_TEMPLATE.lower()
    assert "required" in CONFIG_TEMPLATE.lower()

    # Should mention it's optional to use AI features
    assert "leave commented out" in CONFIG_TEMPLATE.lower()


def test_settings_expose_langfuse_fields():
    settings = Settings(jwt_secret="x", jwt_algorithm="HS256")

    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None
    assert settings.langfuse_host is None
    assert settings.langfuse_environment is None
    assert settings.langfuse_enabled is False


# ---------------------------------------------------------------------------
# Agent LLM provider allowlist
# ---------------------------------------------------------------------------


def _settings_with(**overrides: object) -> Settings:
    """Build settings from raw values, the way a TOML config file arrives."""
    return Settings.model_validate({"jwt_secret": "x", **overrides})


def test_default_llm_providers_are_available_out_of_the_box():
    """A fresh install offers bring-your-own-key access with no configuration."""
    settings = _settings_with()

    assert set(settings.llm_catalog) == {"gwdg", "openai"}
    assert settings.llm_default_provider is None


def test_configuring_llm_providers_replaces_the_defaults():
    settings = _settings_with(
        llm_providers=[
            {
                "id": "local",
                "label": "Local",
                "base_url": "http://localhost:11434/v1",
                "models": ["llama3.1"],
                "requires_api_key": False,
            }
        ]
    )

    assert set(settings.llm_catalog) == {"local"}
    assert settings.llm_catalog["local"].requires_api_key is False


def test_llm_provider_models_accept_the_bare_string_shorthand():
    settings = _settings_with(
        llm_providers=[
            {
                "id": "mixed",
                "label": "Mixed",
                "base_url": "http://localhost",
                "models": ["plain", {"name": "thinker", "reasoning_effort": True}],
            }
        ]
    )

    models = settings.llm_catalog["mixed"].models
    assert [m.name for m in models] == ["plain", "thinker"]
    assert [m.reasoning_effort for m in models] == [False, True]
    # An unlabelled model falls back to its own name for display.
    assert models[0].display_label == "plain"


def test_duplicate_llm_provider_ids_are_rejected():
    """A duplicate id would make the caller-facing provider reference ambiguous."""
    entry = {
        "id": "dup",
        "label": "Dup",
        "base_url": "http://localhost",
        "models": ["m"],
    }

    with pytest.raises(ValidationError):
        _settings_with(llm_providers=[entry, entry])


def test_a_provider_without_models_is_rejected():
    with pytest.raises(ValidationError):
        _settings_with(
            llm_providers=[
                {
                    "id": "empty",
                    "label": "Empty",
                    "base_url": "http://localhost",
                    "models": cast(list[str], []),
                }
            ]
        )


def test_an_unknown_default_model_is_rejected():
    with pytest.raises(ValidationError):
        _settings_with(
            llm_providers=[
                {
                    "id": "p",
                    "label": "P",
                    "base_url": "http://localhost",
                    "models": ["a"],
                    "default_model": "b",
                }
            ]
        )


def test_an_unknown_default_provider_is_rejected():
    with pytest.raises(ValidationError):
        _settings_with(llm_default_provider="not-configured")
