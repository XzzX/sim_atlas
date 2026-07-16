# pyright: basic

import hashlib
from typing import Any

import httpx

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    Annotation,
    FunctionRequest,
)
from sim_atlas_toolkit.settings import ToolkitSettings


async def parse(settings: ToolkitSettings, obj: Any) -> list[httpx.Response]:
    try:
        from python_workflow_definition.models import (  # noqa: PLC0415
            PythonWorkflowDefinitionInputNode,
            PythonWorkflowDefinitionOutputNode,
            PythonWorkflowDefinitionWorkflow,
        )
    except ImportError:
        return []

    if not isinstance(obj, PythonWorkflowDefinitionWorkflow):
        return []

    metadata = FunctionRequest.model_construct()

    metadata.source_code = obj.model_dump_json(indent=2)
    hash = hashlib.sha256(metadata.source_code.encode("utf-8")).hexdigest()
    metadata.hash = hash
    metadata.id = hash

    metadata.inputs = []
    metadata.outputs = []
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            ann = Annotation(label=node.name)
            metadata.inputs.append(ann)
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            ann = Annotation(label=node.name)
            metadata.outputs.append(ann)

    metadata.name = "python_workflow_definition_workflow"
    metadata.python_import = ""
    metadata.category = "workflow"
    metadata.docstring = ""
    metadata.keywords = ["python_workflow_definition"]

    return await node_store_api.create_artifacts(
        settings.api_url, settings.api_token, [metadata]
    )
