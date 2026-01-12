from typing import Any

from node_store_spec.models import NodeType

from .metadata import Metadata


def parse(node: Any) -> Metadata | None:
    from pyiron_workflow.nodes.function import Function

    if not (isinstance(node, type) and issubclass(node, Function)):
        return None

    import hashlib
    import inspect

    source_code = inspect.getsource(node.node_function)
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    inputs = {}
    outputs = {}
    for k, _ in node.preview_inputs().items():
        inputs[k] = None
    for k, _ in node.preview_outputs().items():
        outputs[k] = None

    return Metadata(
        source_code=source_code,
        source_code_hash=source_code_hash,
        inputs=inputs,
        outputs=outputs,
        node_type=NodeType.PYIRON_WORKFLOW_FUNCTION,
    )
