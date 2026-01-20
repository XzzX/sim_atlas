import hashlib
import inspect
from typing import Any

from node_store_spec.models import Annotation, NodeType

from .metadata import Metadata, _parse_annotation


def parse(node: Any) -> Metadata | None:
    if not isinstance(node, type):
        return None

    from pyiron_workflow.api import NOT_DATA  # noqa: PLC0415
    from pyiron_workflow.nodes.function import Function  # noqa: PLC0415

    if not issubclass(node, Function):
        return None

    source_code = inspect.getsource(node.node_function)
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    inputs: dict[str, Annotation] = {}
    outputs: dict[str, Annotation] = {}
    for k, v in node.preview_inputs().items():
        inputs[k] = _parse_annotation(v[0])
        inputs[k].has_default_value = v[1] != NOT_DATA
    for k, v in node.preview_outputs().items():
        outputs[k] = _parse_annotation(v)

    return Metadata(
        node_type=NodeType.PYIRON_WORKFLOW_FUNCTION,
        python_import=f"{node.node_function.__module__}.{node.node_function.__qualname__}",
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring=node.node_function.__doc__ or "",
        inputs=inputs,
        outputs=outputs,
    )
