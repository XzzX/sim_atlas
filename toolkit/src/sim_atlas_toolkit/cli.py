from __future__ import annotations

import argparse
import logging
import os

from sim_atlas_toolkit import upload_modules
from sim_atlas_toolkit.settings import ToolkitSettings

DEFAULT_API_URL_ENV = "SIM_ATLAS_API_URL"
DEFAULT_API_TOKEN_ENV = "SIM_ATLAS_API_TOKEN"
DEFAULT_LLM_URL_ENV = "SIM_ATLAS_LLM_URL"
DEFAULT_LLM_KEY_ENV = "SIM_ATLAS_LLM_KEY"
DEFAULT_LLM_MODEL_ENV = "SIM_ATLAS_LLM_MODEL"

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sim-atlas-upload",
        description=(
            "Upload one or more Python modules to a Sim Atlas backend. "
            "Values can be provided via CLI flags or environment variables."
        ),
    )
    parser.add_argument(
        "modules",
        nargs="+",
        help="Module name(s) to upload, for example 'mypackage.mymodule'.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv(DEFAULT_API_URL_ENV),
        help=(f"Backend API base URL. Defaults to ${DEFAULT_API_URL_ENV} if omitted."),
    )
    parser.add_argument(
        "--api-token",
        default=os.getenv(DEFAULT_API_TOKEN_ENV),
        help=(
            f"API token sent as x-api-key. Defaults to ${DEFAULT_API_TOKEN_ENV} "
            "if omitted."
        ),
    )
    parser.add_argument(
        "--llm-url",
        default=os.getenv(DEFAULT_LLM_URL_ENV),
        help=(f"LLM API base URL. Defaults to ${DEFAULT_LLM_URL_ENV} if omitted."),
    )
    parser.add_argument(
        "--llm-key",
        default=os.getenv(DEFAULT_LLM_KEY_ENV),
        help=(f"LLM API key. Defaults to ${DEFAULT_LLM_KEY_ENV} if omitted."),
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv(DEFAULT_LLM_MODEL_ENV),
        help=(f"LLM model name. Defaults to ${DEFAULT_LLM_MODEL_ENV} if omitted."),
    )
    parser.add_argument(
        "--recursive",
        choices=["no", "import", "filesystem"],
        default="no",
        help="Recursion strategy for module traversal.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing nodes if they already exist.",
    )
    parser.add_argument(
        "--module-allow",
        action="append",
        dest="module_allowlist",
        metavar="MODULE",
        help=(
            "Allow symbols from MODULE (by prefix) even if they are not defined in "
            "the uploaded module. Can be repeated: --module-allow foo --module-allow bar."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper())

    if not args.api_url:
        parser.error(
            f"Missing API URL. Provide --api-url or set {DEFAULT_API_URL_ENV}."
        )
        return 1

    if not args.api_token:
        parser.error(
            f"Missing API token. Provide --api-token or set {DEFAULT_API_TOKEN_ENV}."
        )
        return 1

    settings = ToolkitSettings(
        api_url=args.api_url,
        api_token=args.api_token,
        llm_url=args.llm_url,
        llm_key=args.llm_key,
        llm_model=args.llm_model,
    )

    has_any_llm_option = bool(settings.llm_url or settings.llm_key or settings.llm_model)
    if has_any_llm_option and not settings.enrichment_enabled:
        logger.warning(
            "Incomplete LLM configuration provided. AI enrichment is disabled until "
            "all of --llm-url, --llm-key, and --llm-model are set."
        )

    upload_modules(
        settings=settings,
        modules=args.modules,
        recursive=args.recursive,
        update_existing=args.update_existing,
        module_allowlist=args.module_allowlist,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
