import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimAtlas")

ParserFn: TypeAlias = Callable[..., Awaitable[list[NodeResult]]]

_registered_parsers: list[ParserFn] = []


def register_parser(fn: ParserFn) -> None:
    _registered_parsers.append(fn)
    logger.debug(f"Registered parser: {fn.__module__}.{fn.__qualname__}")


async def get_metadata(
    ctx: ParseContext,
    obj: Any,
    parsers: list[ParserFn] | None,
) -> list[NodeResult]:
    for parser in parsers or _registered_parsers:
        if metadata := await parser(ctx, obj):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
