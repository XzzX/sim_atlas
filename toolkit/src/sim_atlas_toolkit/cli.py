from __future__ import annotations

import argparse
import importlib
import logging
import os

from sim_atlas_toolkit import NodeStore

DEFAULT_API_URL_ENV = "SIM_ATLAS_API_URL"
DEFAULT_API_TOKEN_ENV = "SIM_ATLAS_API_TOKEN"

logger = logging.getLogger("SimAtlas")


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
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    if not args.api_url:
        parser.error(
            f"Missing API URL. Provide --api-url or set {DEFAULT_API_URL_ENV}."
        )

    # Fail fast on import errors so CLI can return a non-zero exit code.
    missing_modules: list[str] = []
    for module_name in args.modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            missing_modules.append(module_name)
            logger.error("Failed to import module %s: %s", module_name, exc)

    if missing_modules:
        logger.error(
            "Aborting upload because one or more modules could not be imported."
        )
        return 1

    store = NodeStore(api_url=args.api_url, api_key=args.api_token)
    for module_name in args.modules:
        store.upload_module(
            module_name,
            update_existing=args.update_existing,
            recursive=args.recursive,
            module_allowlist=args.module_allowlist,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
