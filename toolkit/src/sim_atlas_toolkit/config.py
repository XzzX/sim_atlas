"""Configuration loading for sim-atlas-toolkit.

Settings are merged from the following locations in order (later overrides earlier):

1. System-level:  /etc/sim_atlas/config.toml
2. User-level:    ~/.sim_atlas/config.toml
3. Project-level: ./.sim_atlas/config.toml
"""

import tomllib
import warnings
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    api_url: str = ""
    api_key: str = ""


def _config_paths() -> list[Path]:
    return [
        Path("/etc/sim_atlas/config.toml"),
        Path.home() / ".sim_atlas" / "config.toml",
        Path(".sim_atlas") / "config.toml",
    ]


def load_config(extra_paths: list[Path] | None = None) -> Settings:
    """Load and merge settings from all config file locations.

    Args:
        extra_paths: Additional config file paths appended to the search list
                     (highest priority).

    Returns:
        Settings: Merged configuration with later files taking precedence.
    """
    paths = _config_paths()
    if extra_paths:
        paths.extend(extra_paths)

    merged: dict[str, str] = {}
    for path in paths:
        if path.is_file():
            with path.open("rb") as fh:
                data = tomllib.load(fh)
            for k, v in data.items():
                if isinstance(v, str):
                    merged[k] = v
                else:
                    warnings.warn(
                        f"{path}: ignoring non-string value for key '{k}' ({type(v).__name__})",
                        stacklevel=2,
                    )

    return Settings(
        **{k: v for k, v in merged.items() if k in Settings.__dataclass_fields__}
    )
