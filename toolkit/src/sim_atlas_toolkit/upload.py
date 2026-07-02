import inspect
import logging
from collections.abc import Callable
from typing import Any

import requests

from sim_atlas_toolkit.models import (
    ArtifactRequest,
    FunctionRequest,
    WorkflowRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI

logger = logging.getLogger("SimAtlas")


def upload(
    ns: NodeStoreAPI,
    obj: Any,
    update_existing: bool = False,
    parsers: list[Callable[[Any], list[ArtifactRequest]]] | None = None,
    **kwargs: dict[str, Any],
) -> list[requests.Response]:
    if isinstance(obj, (FunctionRequest, WorkflowRequest)):
        return ns.upload([obj])

    if inspect.ismodule(obj):
        raise ValueError(
            "Will not automatically upload modules. Use upload_module instead."
        )

    from sim_atlas_toolkit.parsers import (  # noqa: PLC0415
        get_metadata,  # avoid circular import
    )

    return get_metadata(obj, parsers, ns)
