import contextlib
import importlib
import importlib.metadata
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

    metadata_list: list[ArtifactRequest] = get_metadata(obj, parsers, ns)

    for metadata in metadata_list:
        with contextlib.suppress(Exception):
            if dependencies := importlib.metadata.requires(
                obj.__module__.partition(".")[0]
            ):
                metadata.dependencies = dependencies

        with contextlib.suppress(Exception):
            package_metadata = importlib.metadata.metadata(
                obj.__module__.partition(".")[0]
            ).json

            if author := package_metadata.get("author"):
                metadata.author_name = author if isinstance(author, str) else author[0]
            if email := package_metadata.get("author_email"):
                metadata.author_email = email if isinstance(email, str) else email[0]
            if project_url := package_metadata.get("project_url"):
                for item in project_url:
                    key, url = item.split(", ")
                    match key.lower():
                        case "homepage":
                            metadata.homepage_url = url
                        case "documentation":
                            metadata.documentation_url = url
                        case "source" | "code" | "repository" | "github":
                            metadata.source_url = url
                        case _:
                            pass

        # metadata_dict.update(kwargs)  # noqa: ERA001

    return ns.upload(metadata_list)
