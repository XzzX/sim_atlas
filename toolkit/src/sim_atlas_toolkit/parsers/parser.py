import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx2

from sim_atlas_toolkit.settings import ToolkitSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimAtlas")

_registered_parsers: list[Callable[..., Awaitable[list[httpx2.Response]]]] = []


def register_parser(fn: Callable[..., Awaitable[list[httpx2.Response]]]) -> None:
    _registered_parsers.append(fn)
    logger.debug(f"Registered parser: {fn.__module__}.{fn.__qualname__}")


async def get_metadata(
    settings: ToolkitSettings,
    obj: Any,
    parsers: list[Callable[..., Awaitable[list[httpx2.Response]]]] | None,
) -> list[httpx2.Response]:
    for parser in parsers or _registered_parsers:
        if metadata := await parser(settings, obj):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
