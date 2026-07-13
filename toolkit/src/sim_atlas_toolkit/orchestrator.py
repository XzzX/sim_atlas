import asyncio
import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any, Literal

import httpx
from tqdm.asyncio import tqdm as atqdm

from sim_atlas_toolkit.collector import collect_objects
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.uploader import upload

logger = logging.getLogger(__name__)


async def _upload_modules_async(  # noqa: PLR0913
    api_url: str,
    api_token: str,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., Awaitable[list[httpx.Response]]]] | None = None,
    module_allowlist: list[str] | None = None,
    concurrency: int = 10,
    **kwargs: dict[str, Any],
) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def upload_object(store: NodeStoreAPI, obj: Any) -> tuple[int, int, int]:
        async with semaphore:
            try:
                responses = await upload(store, obj, update_existing=update_existing)
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

    async with httpx.AsyncClient() as client:
        store = NodeStoreAPI(api_url=api_url, client=client, api_key=api_token)

        for module_name in modules:
            collected_objects = collect_objects(
                module_name,
                recursive=recursive,
                module_allowlist=module_allowlist,
            )
            logger.info(
                f"Collected {len(collected_objects)} objects from {module_name}"
            )

            results: list[tuple[int, int, int]] = await atqdm.gather(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                *[upload_object(store, obj) for obj in collected_objects],
                desc="Uploading objects",
                unit="object",
                total=len(collected_objects),
            )

            created = sum(r[0] for r in results)
            conflicts = sum(r[1] for r in results)
            errors = sum(r[2] for r in results)

            logger.info(
                f"Upload summary for {module_name}: {created} created, {conflicts} conflicts, {errors} errors"
            )


def upload_modules(  # noqa: PLR0913
    api_url: str,
    api_token: str,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., Awaitable[list[httpx.Response]]]] | None = None,
    module_allowlist: list[str] | None = None,
    concurrency: int = 10,
    **kwargs: dict[str, Any],
) -> None:
    asyncio.run(
        _upload_modules_async(
            api_url=api_url,
            api_token=api_token,
            modules=modules,
            recursive=recursive,
            update_existing=update_existing,
            parsers=parsers,
            module_allowlist=module_allowlist,
            concurrency=concurrency,
            **kwargs,
        )
    )
