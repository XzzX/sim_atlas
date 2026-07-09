from collections.abc import Callable
from http import HTTPStatus
import logging
from typing import Any, Literal

import requests

from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.collector import collect_objects
from sim_atlas_toolkit.upload import upload
from tqdm import tqdm

logger = logging.getLogger(__name__)


def upload_modules(
    api_url: str,
    api_token: str,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., list[requests.Response]]] | None = None,
    module_allowlist: list[str] | None = None,
    **kwargs: dict[str, Any],
) -> None:
    store = NodeStoreAPI(api_url=api_url, api_key=api_token)

    for module_name in modules:
        collected_objects = collect_objects(
            module_name,
            recursive=recursive,
            module_allowlist=module_allowlist,
        )
        logger.info(f"Collected {len(collected_objects)} objects from {module_name}")

        created = 0
        conflicts = 0
        errors = 0
        for obj in tqdm(collected_objects, desc="Uploading objects", unit="object"):
            responses = upload(store, obj, update_existing=update_existing)
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
