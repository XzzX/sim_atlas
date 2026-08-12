from __future__ import annotations

import logging
import sys
from typing import Literal

from pydantic import ValidationError, model_validator
from pydantic_settings import CliApp, CliPositionalArg, SettingsConfigDict

from sim_atlas_toolkit import upload_modules
from sim_atlas_toolkit.settings import ToolkitSettings

logger = logging.getLogger(__name__)


class UploadCommand(ToolkitSettings):
    """Upload one or more Python modules to a Sim Atlas backend.

    Every option can also be provided via its SIM_ATLAS_<OPTION> environment
    variable. Docstring enrichment requires the 'ai' extra.
    """

    model_config = SettingsConfigDict(
        cli_prog_name="sim-atlas-upload",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_avoid_json=True,
    )

    modules: CliPositionalArg[list[str]]
    """Module name(s) to upload, for example 'mypackage.mymodule'."""

    # Deliberately narrower than ToolkitSettings, which defaults both to "": an upload
    # cannot run without them, so the CLI reports them as required options.
    api_url: str  # type: ignore[reportGeneralTypeIssues]
    """Backend API base URL."""

    api_token: str  # type: ignore[reportGeneralTypeIssues]
    """API token sent as x-api-key to the backend."""

    recursive: Literal["no", "import", "filesystem"] = "no"
    """Recursion strategy for module traversal."""

    update_existing: bool = False
    """Update existing nodes if they already exist."""

    allowed_modules: list[str] = []
    """Allow symbols from these module prefixes even if they are not defined in the uploaded module. Can be repeated: --allowed-modules foo --allowed-modules bar."""

    concurrency: int = 10
    """Maximum number of concurrent uploads."""

    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    """Logging level."""

    @model_validator(mode="after")
    def _check_llm_config(self) -> UploadCommand:
        if self.llm_docstrings != "no" and not (self.llm_url and self.llm_model):
            raise ValueError(
                "llm_url and llm_model are required when llm_docstrings is enabled"
            )
        return self

    def cli_cmd(self) -> None:
        logging.basicConfig(level=self.log_level.upper())
        upload_modules(
            self,
            modules=self.modules,
            recursive=self.recursive,
            update_existing=self.update_existing,
            module_allowlist=self.allowed_modules,
            concurrency=self.concurrency,
        )


def main() -> int:
    try:
        CliApp.run(UploadCommand)
    except ValidationError as exc:
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"]) or "config"
            print(
                f"sim-atlas-upload: error: {location}: {error['msg']}",
                file=sys.stderr,
            )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
