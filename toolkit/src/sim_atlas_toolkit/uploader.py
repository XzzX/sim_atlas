import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.models import NodeRequest
from sim_atlas_toolkit.node_store import NodeResult

logger = logging.getLogger(__name__)


async def upload(
    ctx: ParseContext,
    obj: Any,
    update_existing: bool = False,
    parsers: list[Callable[..., Awaitable[list[NodeResult]]]] | None = None,
    **kwargs: dict[str, Any],
) -> list[NodeResult]:
    if isinstance(obj, NodeRequest):
        return await ctx.store.create_nodes([obj])

    if inspect.ismodule(obj):
        raise ValueError(
            "Will not automatically upload modules. Use upload_module instead."
        )

    from sim_atlas_toolkit.parsers import (  # noqa: PLC0415
        get_metadata,  # avoid circular import
    )

    return await get_metadata(ctx, obj, parsers)
