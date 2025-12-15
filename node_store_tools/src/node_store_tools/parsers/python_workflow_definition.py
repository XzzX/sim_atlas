from typing import Any

from node_store_spec.models import NodeType
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

    source_code = obj.dump_json()
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    arguments = {}
    returns_unpacked = {}
    for node in obj.nodes:
        if isinstance(node, PythonWorkflowDefinitionInputNode):
            arguments[node.name] = None
        if isinstance(node, PythonWorkflowDefinitionOutputNode):
            returns_unpacked[node.name] = None

    return Metadata(
        source_code=source_code,
        source_code_hash=source_code_hash,
        arguments=arguments,
        returns_unpacked=returns_unpacked,
        node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
    )
