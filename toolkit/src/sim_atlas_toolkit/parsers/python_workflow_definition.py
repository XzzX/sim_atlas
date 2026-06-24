# pyright: basic

from typing import Any

from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactRequest,
    FunctionRequest,
)
from sim_atlas_toolkit.node_store_api import NodeStoreAPI


def parse(obj: Any, _: NodeStoreAPI) -> list[ArtifactRequest]:
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

    return [metadata]
