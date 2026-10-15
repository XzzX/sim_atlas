import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_CONFIG_FILES = [
    Path("/etc/sim_atlas_config.toml"),  # system (lowest priority)
    Path.home() / ".sim_atlas_config.toml",  # user
    Path(".sim_atlas_config.toml"),  # working directory (highest among files)
]


def _get_config_files() -> list[str]:
    """Get list of config file paths to search for."""
    return [str(p) for p in _CONFIG_FILES]


CONFIG_TEMPLATE = """# Sim Atlas Configuration Template
# Fill in required fields, uncomment and configure optional sections as needed.
# After editing, restart the server.

# === REQUIRED SETTINGS ===

# JWT Secret Key for signing access tokens.
# Generate a strong random key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
# This is used to sign and verify API authentication tokens.
# Minimum recommended length: 32 characters
jwt_secret = "replace-with-strong-secret-key-min-32-chars"

# === OPTIONAL: JWT SETTINGS ===
# JWT Algorithm for token signing (default: HS256)
# Override only if you need a different algorithm.
# Common values: HS256 (HMAC with SHA-256), HS512 (HMAC with SHA-512)
# jwt_algorithm = "HS256"

# === OPTIONAL: EMBEDDINGS ===
# Leave commented out if you don't use semantic search (keyword search still works).
# Configure the embedding provider for semantic search.
embedding_provider = "fastembed"                    # fastembed | openai | voyageai
embedding_model = "nomic-ai/nomic-embed-text-v1.5"  # model name
# embedding_api_key = "pa-..."                      # API key (voyageai or openai; omit for fastembed)
# embedding_base_url = "https://..."                # base URL for openai-compatible endpoint (openai provider only)
embedding_batch_size = 8                            # number of documents per embedding batch
"""


class Settings(BaseSettings):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    embedding_provider: Literal["fastembed", "openai", "voyageai"] | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_batch_size: int = 8

    model_config = SettingsConfigDict(
        toml_file=_get_config_files(),
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SIM_ATLAS_",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
        )

    @property
    def config_dir(self) -> Path:
        """Directory of the highest-priority config file that exists, or cwd."""
        for path in reversed(_CONFIG_FILES):  # highest priority first
            if path.exists():
                return path.parent
        return Path(".")

    @property
    def embeddings_enabled(self) -> bool:
        match self.embedding_provider:
            case "fastembed":
                return True
            case "openai" | "voyageai":
                return bool(self.embedding_api_key and self.embedding_model)
            case _:
                return False


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """
    Load settings from environment, .env file, or TOML config files.

    On the first startup, if no config file exists and required settings are
    missing, generates a strong JWT secret, writes a config file, and continues
    loading without requiring a restart.

    Returns:
        Settings: Validated settings instance

    Raises:
        ValidationError: When config file exists but contains invalid values
    """
    try:
        return Settings.model_validate({})
    except ValidationError as e:
        # Check if any config file exists
        config_exists = any(path.exists() for path in _CONFIG_FILES)

        if not config_exists:
            # Check if any required fields are actually missing
            # by examining the error details
            missing_required = any(
                error.get("type") == "missing" for error in e.errors()
            )

            if missing_required:
                # Generate a strong JWT secret so the server can start immediately
                jwt_secret = secrets.token_urlsafe(32)
                config_content = CONFIG_TEMPLATE.replace(
                    'jwt_secret = "replace-with-strong-secret-key-min-32-chars"',
                    f'jwt_secret = "{jwt_secret}"',
                )

                # Write config to working directory
                config_path = _CONFIG_FILES[2]  # .sim_atlas_config.toml
                config_path.parent.mkdir(parents=True, exist_ok=True)
                # Owner-only: the file contains the JWT secret
                fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(config_content)

                # Inform the user
                print(
                    f"\n{'=' * 70}",
                    "New configuration file created:",
                    f"{config_path.absolute()}",
                    f"{'=' * 70}",
                    "\nA strong JWT secret has been generated and saved automatically.",
                    "You can check the configuration and restart the server if you want.",
                    f"{'=' * 70}\n",
                    sep="\n",
                    file=sys.stderr,
                )

                # Clear the lru_cache so the newly written file is picked up
                load_settings.cache_clear()
                return Settings.model_validate({})

        # If config exists or error is not about missing fields, re-raise
        raise


# Load settings on import
settings = load_settings()
