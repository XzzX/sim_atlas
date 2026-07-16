# pyright: basic

import hashlib
import inspect
from typing import Any

import httpx

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    ArtifactType,
    FunctionRequest,
)
from sim_atlas_toolkit.parsers.metadata import (
    enrich_metadata,
    parse_annotation,
)
from sim_atlas_toolkit.settings import ToolkitSettings


async def parse(settings: ToolkitSettings, node: Any) -> list[httpx.Response]:
    if not isinstance(node, type):
        return []

    try:
        from pyiron_workflow.api import NOT_DATA  # noqa: PLC0415
        from pyiron_workflow.nodes.function import Function  # noqa: PLC0415
    except ImportError:
        return []

    if not issubclass(node, Function):
        return []

    metadata = FunctionRequest.model_construct()

    metadata.source_code = inspect.getsource(node.node_function)
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    metadata.inputs = []
    metadata.outputs = []
    for k, v in node.preview_inputs().items():
        ann = parse_annotation(v[0])
        ann.label = k
        ann.has_default_value = v[1] != NOT_DATA
        metadata.inputs.append(ann)
    for k, v in node.preview_outputs().items():
        ann = parse_annotation(v)
        ann.label = k
        metadata.outputs.append(ann)

    metadata.name = f"{node.node_function.__module__}.{node.node_function.__qualname__}"
    metadata.artifact_type = ArtifactType.FUNCTION
    metadata.python_import = (
        f"{node.node_function.__module__}.{node.node_function.__qualname__}"
    )
    metadata.category = f"{node.node_function.__module__}".replace(".", ">")
    metadata.docstring = node.node_function.__doc__ or ""
    metadata.keywords = ["pyiron_workflow_function"]

    await enrich_metadata(settings, metadata)

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )
