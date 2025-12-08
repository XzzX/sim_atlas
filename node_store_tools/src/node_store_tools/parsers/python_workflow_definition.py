from node_store_spec.models import NodeType
from python_workflow_definition.models import (
    PythonWorkflowDefinitionInputNode,
    PythonWorkflowDefinitionOutputNode,
    PythonWorkflowDefinitionWorkflow,
)

from .metadata import Metadata


def extract_metadata(workflow: PythonWorkflowDefinitionWorkflow) -> Metadata:
    import hashlib

    source_code = workflow.dump_json()
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    arguments = {}
    returns_unpacked = {}
    for node in workflow.nodes:
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


parsers = {
    PythonWorkflowDefinitionWorkflow: extract_metadata,
}
