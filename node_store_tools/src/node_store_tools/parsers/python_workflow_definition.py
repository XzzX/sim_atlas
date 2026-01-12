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

    import hashlib

    source_code: str = obj.dump_json()
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    inputs: dict[str, Annotation] = {}
    outputs: dict[str, Annotation] = {}
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            inputs[node.name] = Annotation()
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            outputs[node.name] = Annotation()

    return Metadata(
        source_code=source_code,
        source_code_hash=source_code_hash,
        inputs=inputs,
        outputs=outputs,
        node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
    )
