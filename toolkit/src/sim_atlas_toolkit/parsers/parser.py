import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.settings import ToolkitSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimAtlas")

_registered_parsers: list[Callable[..., Awaitable[list[httpx.Response]]]] = []


def register_parser(fn: Callable[..., Awaitable[list[httpx.Response]]]) -> None:
    _registered_parsers.append(fn)
    logger.debug(f"Registered parser: {fn.__module__}.{fn.__qualname__}")


async def get_metadata(
    settings: ToolkitSettings,
    obj: Any,
    parsers: list[Callable[..., Awaitable[list[httpx.Response]]]] | None,
    ns: NodeStoreAPI,
) -> list[httpx.Response]:
    for parser in parsers or _registered_parsers:
        if metadata := await parser(settings, obj, ns):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
