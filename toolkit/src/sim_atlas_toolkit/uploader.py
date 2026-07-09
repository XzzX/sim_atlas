import inspect
import logging
from collections.abc import Callable
from typing import Any

import requests

from sim_atlas_toolkit.models import (
    FunctionRequest,
    WorkflowRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.settings import ToolkitSettings

logger = logging.getLogger(__name__)


def upload(
    ns: NodeStoreAPI,
    obj: Any,
    settings: ToolkitSettings,
    update_existing: bool = False,
    parsers: list[Callable[..., list[requests.Response]]] | None = None,
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

    return get_metadata(obj, parsers, ns, settings)
