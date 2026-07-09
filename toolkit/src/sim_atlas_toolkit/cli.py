from __future__ import annotations

import argparse
import logging
import os
from http import HTTPStatus

from toolkit.src.sim_atlas_toolkit import upload
from toolkit.src.sim_atlas_toolkit.collector import collect_objects
from tqdm import tqdm

from sim_atlas_toolkit import NodeStoreAPI

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
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level.",
    )
    return parser


def upload_modules(modules: list[str], api_url: str, api_token: str) -> None:
    store = NodeStoreAPI(api_url=api_url, api_key=api_token)

    for module_name in modules:
        collected_objects = collect_objects(
            module_name,
            recursive=args.recursive,
            module_allowlist=args.module_allowlist,
        )
        logger.info(f"Collected {len(collected_objects)} objects from {module_name}")

        created = 0
        conflicts = 0
        errors = 0
        for obj in tqdm(collected_objects, desc="Uploading objects", unit="object"):
            responses = upload(store, obj, update_existing=args.update_existing)
            if not responses:
                logger.warning(f"No responses received for object {obj}")
                errors += 1
                continue
            for response in responses:
                if response.status_code == HTTPStatus.CREATED:
                    created += 1
                elif response.status_code == HTTPStatus.CONFLICT:
                    conflicts += 1
                else:
                    errors += 1

    logger.info(
        f"Upload summary for {module_name}: {created} created, {conflicts} conflicts, {errors} errors"
    )


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    if not args.api_url:
        parser.error(
            f"Missing API URL. Provide --api-url or set {DEFAULT_API_URL_ENV}."
        )
        raise SystemExit(1)

    upload_modules(
        modules=args.modules,
        api_url=args.api_url,
        api_token=args.api_token,
    )
