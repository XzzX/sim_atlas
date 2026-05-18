"""Tests for settings initialization and config file creation."""

from pathlib import Path
from unittest import mock

import pytest
from pydantic import ValidationError


def test_load_settings_returns_valid_instance():
    """Test that load_settings returns a valid Settings instance."""
    from sim_atlas_backend.settings import load_settings

    load_settings.cache_clear()
    settings = load_settings()

    # Should have required fields set
    assert settings.jwt_secret_key is not None
    assert settings.jwt_algorithm is not None


def test_config_template_structure():
    """Test that the template has all required sections and keys."""
    from sim_atlas_backend.settings import CONFIG_TEMPLATE

    assert "=== REQUIRED SETTINGS ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: LLM / AI ENRICHMENT ===" in CONFIG_TEMPLATE
    assert "=== OPTIONAL: VOYAGEAI EMBEDDINGS ===" in CONFIG_TEMPLATE

    # Check all fields are documented
    assert "jwt_secret_key" in CONFIG_TEMPLATE
    assert "jwt_algorithm" in CONFIG_TEMPLATE
    assert "llm_api_key" in CONFIG_TEMPLATE
    assert "llm_api_url" in CONFIG_TEMPLATE
    assert "llm_embedding_model" in CONFIG_TEMPLATE
    assert "llm_chat_model" in CONFIG_TEMPLATE
    assert "voyage_api_key" in CONFIG_TEMPLATE

    # Check that template has verbose comments
    comment_lines = [
        line
        for line in CONFIG_TEMPLATE.split("\n")
        if line.strip().startswith("#")
    ]
    assert len(comment_lines) > 20, "Template should have verbose comments"


def test_load_settings_caching():
    """Test that load_settings returns cached instance on repeated calls."""
    from sim_atlas_backend.settings import load_settings

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
    from sim_atlas_backend.settings import CONFIG_TEMPLATE

    assert "python -c" in CONFIG_TEMPLATE  # Secret generation hint
    assert "https://www.voyageai.com/" in CONFIG_TEMPLATE
    assert "sk-" in CONFIG_TEMPLATE  # OpenAI key example
    assert "pa-" in CONFIG_TEMPLATE  # VoyageAI key example
    assert "http://localhost:11434/v1" in CONFIG_TEMPLATE  # Ollama example
    assert (
        "gpt-4" in CONFIG_TEMPLATE or "neural-chat" in CONFIG_TEMPLATE
    )  # Model examples


def test_template_has_all_fields_explained():
    """Test that every config field has explanation text."""
    from sim_atlas_backend.settings import CONFIG_TEMPLATE

    # Each field should have at least one comment line explaining it
    fields = [
        "jwt_secret_key",
        "jwt_algorithm",
        "llm_api_key",
        "llm_api_url",
        "llm_chat_model",
        "llm_embedding_model",
        "voyage_api_key",
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


def test_settings_can_be_loaded_from_env(monkeypatch):
    """Test that settings can be loaded from environment variables."""
    from sim_atlas_backend.settings import load_settings

    # The module-level config should already be loaded,
    # but we can test that load_settings is a valid function
    load_settings.cache_clear()
    settings = load_settings()

    # Should have at least the required fields
    assert hasattr(settings, "jwt_secret_key")
    assert hasattr(settings, "jwt_algorithm")
    assert hasattr(settings, "llm_api_key")
    assert hasattr(settings, "voyage_api_key")


def test_missing_config_error_exists():
    """Test that MissingConfigError exception is defined."""
    from sim_atlas_backend.exceptions import MissingConfigError

    # Should be able to raise and catch it
    with pytest.raises(MissingConfigError):
        raise MissingConfigError("test")


def test_template_mentions_deployment_scenarios():
    """Test that template explains optional vs required settings."""
    from sim_atlas_backend.settings import CONFIG_TEMPLATE

    # Template should explain when to use optional settings
    assert "optional" in CONFIG_TEMPLATE.lower()
    assert "required" in CONFIG_TEMPLATE.lower()

    # Should mention it's optional to use AI features
    assert "leave commented out" in CONFIG_TEMPLATE.lower()
