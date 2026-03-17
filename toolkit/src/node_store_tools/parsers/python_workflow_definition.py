import hashlib
from typing import Any

from node_store_spec.models import Annotation, NodeType
from python_workflow_definition.models import (
    PythonWorkflowDefinitionInputNode,
    PythonWorkflowDefinitionOutputNode,
    PythonWorkflowDefinitionWorkflow,
)

from .metadata import Metadata


def parse(obj: Any) -> Metadata | None:
    if not isinstance(obj, PythonWorkflowDefinitionWorkflow):
        return None

    source_code: str = obj.model_dump_json()
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    inputs: list[Annotation] = []
    outputs: list[Annotation] = []
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            ann = Annotation(label=node.name)
            inputs.append(ann)
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            ann = Annotation(label=node.name)
            outputs.append(ann)

    return Metadata(
        node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
        python_import=None,
        category="workflow",
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring="",
        keywords=[],
        inputs=inputs,
        outputs=outputs,
    )
