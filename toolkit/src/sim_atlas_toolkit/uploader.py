import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from sim_atlas_toolkit.models import (
    FunctionRequest,
    WorkflowRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI

logger = logging.getLogger(__name__)


async def upload(
    ns: NodeStoreAPI,
    obj: Any,
    update_existing: bool = False,
    parsers: list[Callable[[Any], Awaitable[list[httpx.Response]]]] | None = None,
    **kwargs: dict[str, Any],
) -> list[httpx.Response]:
    if isinstance(obj, (FunctionRequest, WorkflowRequest)):
        return await ns.upload([obj])

    if inspect.ismodule(obj):
        raise ValueError(
            "Will not automatically upload modules. Use upload_module instead."
        )

    from sim_atlas_toolkit.parsers import (  # noqa: PLC0415
        get_metadata,  # avoid circular import
    )

    return await get_metadata(obj, parsers, ns)
