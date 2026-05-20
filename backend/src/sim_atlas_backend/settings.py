import sys
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from .exceptions import MissingConfigError

_CONFIG_FILES = [
    Path("/etc/sim_atlas/config.toml"),  # system (lowest priority)
    Path.home() / ".sim_atlas" / "config.toml",  # user
    Path(".sim_atlas") / "config.toml",  # working directory (highest among files)
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
jwt_secret_key = "replace-with-strong-secret-key-min-32-chars"

# JWT Algorithm for token signing (standard: HS256)
# Determines the cryptographic algorithm for token signing.
# Common values: HS256 (HMAC with SHA-256), HS512 (HMAC with SHA-512)
jwt_algorithm = "HS256"

# === OPTIONAL: LLM / AI ENRICHMENT ===
# Leave commented out if you don't use AI features (semantic search, docstring enrichment).
# If any of these are configured, AI endpoints will be enabled in the API.

# OpenAI-compatible LLM API Key
# Used for generating refined docstrings and AI agent features.
# Examples: OpenAI (sk-...), LocalAI, Ollama via OpenAI-compatible endpoint
# llm_api_key = "sk-..."

# OpenAI-compatible LLM API URL
# Base URL of the OpenAI-compatible API server.
# Examples: https://chat-ai.academiccloud.de/v1/ (GWDG)
#           http://localhost:11434/v1 (Ollama local)
# Must be a valid HTTP(S) URL.
# llm_api_url = "https://chat-ai.academiccloud.de/v1/"

# LLM Chat Model Name
# Name of the model to use for conversational docstring refinement.
# llm_chat_model = "qwen3.5-27b"

# LLM Embedding Model Name
# Name of the model to use for generating text embeddings.
# Required only if using embedding-based semantic search.
# Examples: text-embedding-3-small (OpenAI), nomic-embed-text (Ollama)
# llm_embedding_model = "multilingual-e5-large-instruct"

# LLM Enrichment Concurrency
# Maximum number of simultaneous LLM requests during bulk enrichment.
# Lower values reduce API load; higher values speed up large batches.
# llm_enrich_concurrency = 5

# === OPTIONAL: VOYAGEAI EMBEDDINGS ===
# Alternative to LLM-based embeddings; uses VoyageAI's hosted API.
# Choose either LLM embedding OR VoyageAI, not both.

# VoyageAI API Key
# Required for semantic search via VoyageAI (voyage-code-3 model).
# Get an API key from https://www.voyageai.com/
# Only needed if using VoyageAI instead of llm_embedding_model.
# voyage_api_key = "pa-..."

# === OPTIONAL: LANGFUSE OBSERVABILITY ===
# Enable this only if you want to export agent traces to Langfuse.
# Tracing is enabled when all of the fields below are set.
# Install the optional dependency with: uv sync --extra langfuse

# Langfuse Public Key
# Used to authenticate trace writes to Langfuse.
# langfuse_public_key = "pk-lf-..."

# Langfuse Secret Key
# Used with the public key to sign trace writes.
# langfuse_secret_key = "sk-lf-..."

# Langfuse Host URL
# Base URL for your Langfuse deployment.
# Examples: https://cloud.langfuse.com, http://localhost:3000
# langfuse_host = "https://cloud.langfuse.com"

# Langfuse Environment
# Optional environment label shown in Langfuse.
# langfuse_environment = "development"
"""


class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str
    llm_api_key: str | None = None
    llm_api_url: str | None = None
    llm_embedding_model: str | None = None
    llm_chat_model: str | None = None
    llm_enrich_concurrency: int = 5
    voyage_api_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    langfuse_environment: str | None = None

    model_config = SettingsConfigDict(
        toml_file=_get_config_files(),
        env_file=".env",
        env_file_encoding="utf-8",
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
    def langfuse_enabled(self) -> bool:
        return bool(
            self.langfuse_public_key and self.langfuse_secret_key and self.langfuse_host
        )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """
    Load settings from environment, .env file, or TOML config files.

    If required settings are missing and no config file exists in any location,
    creates a verbose template at .sim_atlas/config.toml and raises MissingConfigError.

    Returns:
        Settings: Validated settings instance

    Raises:
        MissingConfigError: When required fields are missing and template is created
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
                # Create template in working directory
                config_path = _CONFIG_FILES[2]  # .sim_atlas/config.toml
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(CONFIG_TEMPLATE)

                # Print helpful message to stderr
                print(
                    f"\n{'=' * 70}",
                    f"Configuration file created: {config_path.absolute()}",
                    f"{'=' * 70}",
                    "\nRequired fields to fill in:",
                    "  - jwt_secret_key: A strong secret key for signing tokens",
                    "  - jwt_algorithm: Usually 'HS256'",
                    "\nOptional fields (AI/semantic search):",
                    "  - llm_api_key, llm_api_url, llm_chat_model, llm_embedding_model",
                    "  - voyage_api_key",
                    "  - langfuse_public_key, langfuse_secret_key, langfuse_host",
                    "\nPlease review the config file, fill in the required fields,",
                    "and restart the server.",
                    f"{'=' * 70}\n",
                    sep="\n",
                    file=sys.stderr,
                )

                raise MissingConfigError(
                    f"Configuration file created at {config_path.absolute()}. "
                    "Please fill in required fields and restart."
                ) from e

        # If config exists or error is not about missing fields, re-raise
        raise


# Load settings on import; exit gracefully if template is created
try:
    settings = load_settings()
except MissingConfigError:
    sys.exit(2)
