import asyncio
import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal

import requests
from tqdm import tqdm

from sim_atlas_toolkit.collector import collect_objects
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.settings import ToolkitSettings
from sim_atlas_toolkit.uploader import upload

logger = logging.getLogger(__name__)


async def _upload_modules_async(  # noqa: PLR0913
    settings: ToolkitSettings,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., list[requests.Response]]] | None = None,
    module_allowlist: list[str] | None = None,
    **kwargs: dict[str, Any],
) -> None:
    store = NodeStoreAPI(api_url=settings.api_url, api_key=settings.api_token)
    semaphore = asyncio.Semaphore(10)

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

        async def upload_object(obj: Any) -> tuple[int, int, int]:
            async with semaphore:
                try:
                    responses = await asyncio.to_thread(
                        upload,
                        store,
                        obj,
                        settings,
                        update_existing=update_existing,
                        parsers=parsers,
                    )
                except Exception:
                    logger.exception("Failed to upload object %s", obj)
                    return 0, 0, 1

                if not responses:
                    logger.warning(f"No responses received for object {obj}")
                    return 0, 0, 1

                object_created = 0
                object_conflicts = 0
                object_errors = 0
                for response in responses:
                    if response.status_code == HTTPStatus.CREATED:
                        object_created += 1
                    elif response.status_code == HTTPStatus.CONFLICT:
                        object_conflicts += 1
                    else:
                        object_errors += 1

                return object_created, object_conflicts, object_errors

        tasks = [asyncio.create_task(upload_object(obj)) for obj in collected_objects]
        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Uploading objects",
            unit="object",
        ):
            object_created, object_conflicts, object_errors = await task
            created += object_created
            conflicts += object_conflicts
            errors += object_errors

        logger.info(
            f"Upload summary for {module_name}: {created} created, {conflicts} conflicts, {errors} errors"
        )


def upload_modules(  # noqa: PLR0913
    settings: ToolkitSettings,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., list[requests.Response]]] | None = None,
    module_allowlist: list[str] | None = None,
    **kwargs: dict[str, Any],
) -> None:
    asyncio.run(
        _upload_modules_async(
            settings=settings,
            modules=modules,
            recursive=recursive,
            update_existing=update_existing,
            parsers=parsers,
            module_allowlist=module_allowlist,
            **kwargs,
        )
    )
