import logging
from collections.abc import Callable
from typing import Any

import requests

from sim_atlas_toolkit.node_store_api import NodeStoreAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimAtlas")

_registered_parsers: list[Callable[..., list[requests.Response]]] = []


def register_parser(fn: Callable[..., list[requests.Response]]) -> None:
    _registered_parsers.append(fn)
    logger.info(f"Registered parser: {fn.__module__}.{fn.__qualname__}")


def get_metadata(
    obj: Any,
    parsers: list[Callable[..., list[requests.Response]]] | None,
    ns: NodeStoreAPI,
) -> list[requests.Response]:
    for parser in parsers or _registered_parsers:
        if metadata := parser(obj, ns):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
