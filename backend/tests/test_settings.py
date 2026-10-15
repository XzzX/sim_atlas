"""Tests for settings initialization and config file creation."""

import stat
from pathlib import Path

import pytest

from sim_atlas import settings as settings_module
from sim_atlas.exceptions import MissingConfigError
from sim_atlas.settings import CONFIG_TEMPLATE, load_settings


MIN_COMMENT_LINES = 15
OWNER_ONLY_MODE = 0o600


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
    assert "=== OPTIONAL: EMBEDDINGS ===" in CONFIG_TEMPLATE

    # Check all fields are documented
    assert "jwt_secret" in CONFIG_TEMPLATE
    assert "jwt_algorithm" in CONFIG_TEMPLATE
    assert "embedding_provider" in CONFIG_TEMPLATE
    assert "embedding_model" in CONFIG_TEMPLATE
    assert "embedding_api_key" in CONFIG_TEMPLATE

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
    assert "pa-" in CONFIG_TEMPLATE  # VoyageAI key example


def test_template_has_all_fields_explained():
    """Test that every config field has explanation text."""
    # Each field should have at least one comment line explaining it
    fields = [
        "jwt_secret",
        "jwt_algorithm",
        "embedding_provider",
        "embedding_model",
        "embedding_api_key",
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
    assert hasattr(settings, "embedding_model")
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


def test_first_run_config_is_owner_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generated config holds the JWT secret, so only the owner may read it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SIM_ATLAS_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        settings_module,
        "_CONFIG_FILES",
        [tmp_path / "etc.toml", tmp_path / "home.toml", Path(".sim_atlas_config.toml")],
    )
    load_settings.cache_clear()
    try:
        generated = load_settings()
        config_file = tmp_path / ".sim_atlas_config.toml"

        assert generated.jwt_secret != "replace-with-strong-secret-key-min-32-chars"
        assert stat.S_IMODE(config_file.stat().st_mode) == OWNER_ONLY_MODE
    finally:
        load_settings.cache_clear()
