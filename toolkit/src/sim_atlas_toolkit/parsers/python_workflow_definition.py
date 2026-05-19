# pyright: basic

from typing import Any

from ..models import Annotation, NodeType
from .metadata import Metadata


def parse(obj: Any) -> list[Metadata]:
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

    source_code: str = obj.model_dump_json(indent=2)

    inputs: list[Annotation] = []
    outputs: list[Annotation] = []
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            ann = Annotation(label=node.name)
            inputs.append(ann)
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            ann = Annotation(label=node.name)
            outputs.append(ann)

    return [
        Metadata(
            node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
            python_import="",
            category="workflow",
            source_code=source_code,
            docstring="",
            keywords=[],
            inputs=inputs,
            outputs=outputs,
        )
    ]
