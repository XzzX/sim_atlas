from __future__ import annotations

import argparse
import logging
import os

from sim_atlas_toolkit import upload_modules
from sim_atlas_toolkit.settings import EnrichmentSettings

DEFAULT_API_URL_ENV = "SIM_ATLAS_API_URL"
DEFAULT_API_TOKEN_ENV = "SIM_ATLAS_API_TOKEN"

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
        "--concurrency",
        type=int,
        default=10,
        help="Maximum number of concurrent uploads.",
    )
    parser.add_argument(
        "--enrich-docstrings",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Generate docstrings from source code via an LLM before parsing. "
            "Defaults to $SIM_ATLAS_LLM_ENABLED. Requires the 'ai' extra."
        ),
    )
    parser.add_argument(
        "--llm-url",
        default=None,
        help="OpenAI-compatible base URL. Defaults to $SIM_ATLAS_LLM_URL.",
    )
    parser.add_argument(
        "--llm-key",
        default=None,
        help="API key for the LLM service. Defaults to $SIM_ATLAS_LLM_KEY.",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model name. Defaults to $SIM_ATLAS_LLM_MODEL.",
    )
    parser.add_argument(
        "--overwrite-docstrings",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Regenerate docstrings even when one already exists. "
            "Defaults to $SIM_ATLAS_LLM_OVERWRITE."
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

    overrides = {
        k: v
        for k, v in {
            "enabled": args.enrich_docstrings,
            "url": args.llm_url,
            "key": args.llm_key,
            "model": args.llm_model,
            "overwrite": args.overwrite_docstrings,
        }.items()
        if v is not None
    }
    enrichment_settings = EnrichmentSettings(**overrides)

    if enrichment_settings.enabled and not (
        enrichment_settings.url and enrichment_settings.model
    ):
        parser.error(
            "Docstring enrichment is enabled but the LLM URL or model is missing. "
            "Provide --llm-url/--llm-model or set SIM_ATLAS_LLM_URL/SIM_ATLAS_LLM_MODEL."
        )
        return 1

    upload_modules(
        api_url=args.api_url,
        api_token=args.api_token,
        modules=args.modules,
        recursive=args.recursive,
        update_existing=args.update_existing,
        module_allowlist=args.module_allowlist,
        concurrency=args.concurrency,
        enrichment_settings=enrichment_settings,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
