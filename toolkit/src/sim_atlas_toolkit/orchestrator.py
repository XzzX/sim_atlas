import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal

from tqdm.asyncio import tqdm as atqdm

from sim_atlas_toolkit.collector import collect_objects
from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.http_node_store import HttpNodeStore
from sim_atlas_toolkit.node_store import (
    EmbeddingNotConfiguredError,
    NodeResult,
    NodeStatus,
    NodeStore,
    NodeStoreError,
)
from sim_atlas_toolkit.settings import ToolkitSettings
from sim_atlas_toolkit.uploader import upload

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ModuleUploadResult:
    """Per-module outcome of `upload_modules`."""

    module: str
    created: int
    existing: int
    errors: int


async def _upload_modules_async(  # noqa: PLR0913
    settings: ToolkitSettings,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., Awaitable[list[NodeResult]]]] | None = None,
    module_allowlist: list[str] | None = None,
    concurrency: int = 10,
    store: NodeStore | None = None,
    **kwargs: dict[str, Any],
) -> list[ModuleUploadResult]:
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    upload_all = partial(
        _upload_with_context,
        modules=modules,
        recursive=recursive,
        update_existing=update_existing,
        parsers=parsers,
        module_allowlist=module_allowlist,
        concurrency=concurrency,
        **kwargs,
    )
    # A caller-supplied store belongs to the caller and stays open; a store
    # created here is closed when the upload finishes.
    if store is not None:
        return await upload_all(ParseContext(settings=settings, store=store))
    async with HttpNodeStore(settings.api_url, settings.api_token) as owned:
        return await upload_all(ParseContext(settings=settings, store=owned))


async def _upload_with_context(  # noqa: PLR0913
    ctx: ParseContext,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"],
    update_existing: bool,
    parsers: list[Callable[..., Awaitable[list[NodeResult]]]] | None,
    module_allowlist: list[str] | None,
    concurrency: int,
    **kwargs: dict[str, Any],
) -> list[ModuleUploadResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def upload_object(obj: Any) -> tuple[int, int, int]:
        async with semaphore:
            try:
                node_results = await upload(
                    ctx,
                    obj,
                    update_existing=update_existing,
                    parsers=parsers,
                    **kwargs,
                )
            except Exception:
                logger.exception("Failed to upload object %s", obj)
                return 0, 0, 1

            if not node_results:
                logger.warning(f"No results received for object {obj}")
                return 0, 0, 1

            created = sum(
                1 for result in node_results if result.status is NodeStatus.CREATED
            )
            return created, len(node_results) - created, 0

    summaries: list[ModuleUploadResult] = []
    for module_name in modules:
        collected_objects = collect_objects(
            module_name,
            recursive=recursive,
            module_allowlist=module_allowlist,
        )
        logger.info(f"Collected {len(collected_objects)} objects from {module_name}")

        results: list[tuple[int, int, int]] = await atqdm.gather(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            *[upload_object(obj) for obj in collected_objects],
            desc="Uploading objects",
            unit="object",
            total=len(collected_objects),
        )

        created = sum(r[0] for r in results)
        existing = sum(r[1] for r in results)
        errors = sum(r[2] for r in results)

        logger.info(
            f"Upload summary for {module_name}: {created} created, {existing} existing, {errors} errors"
        )
        summaries.append(
            ModuleUploadResult(
                module=module_name, created=created, existing=existing, errors=errors
            )
        )

    if ctx.settings.embed:
        try:
            await ctx.store.trigger_embed()
            logger.info("Triggered embedding of newly uploaded nodes")
        except EmbeddingNotConfiguredError:
            logger.warning(
                "Skipped embedding: backend has no embedding provider configured"
            )
        except NodeStoreError as exc:
            logger.warning(f"Embedding request failed: {exc}")
        except Exception:
            logger.exception("Failed to trigger embedding")

    return summaries


def upload_modules(  # noqa: PLR0913
    settings: ToolkitSettings,
    modules: list[str],
    recursive: Literal["no", "import", "filesystem"] = "no",
    update_existing: bool = False,
    parsers: list[Callable[..., Awaitable[list[NodeResult]]]] | None = None,
    module_allowlist: list[str] | None = None,
    concurrency: int = 10,
    store: NodeStore | None = None,
    **kwargs: dict[str, Any],
) -> list[ModuleUploadResult]:
    async def run() -> list[ModuleUploadResult]:
        try:
            return await _upload_modules_async(
                settings,
                modules=modules,
                recursive=recursive,
                update_existing=update_existing,
                parsers=parsers,
                module_allowlist=module_allowlist,
                concurrency=concurrency,
                store=store,
                **kwargs,
            )
        finally:
            # The event loop ends with this call. Release the caller's store
            # from it; the store stays usable for the next call.
            if store is not None:
                await store.aclose()

    return asyncio.run(run())
