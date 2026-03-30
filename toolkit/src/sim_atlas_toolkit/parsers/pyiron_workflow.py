import hashlib
import inspect
from typing import Any

from ..models import Annotation, NodeType
from .metadata import Metadata, parse_annotation


def parse(node: Any) -> Metadata | None:
    if not isinstance(node, type):
        return None

    from pyiron_workflow.api import NOT_DATA  # noqa: PLC0415
    from pyiron_workflow.nodes.function import Function  # noqa: PLC0415

    if not issubclass(node, Function):
        return None

    source_code = inspect.getsource(node.node_function)
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    inputs: list[Annotation] = []
    outputs: list[Annotation] = []
    for k, v in node.preview_inputs().items():
        ann = parse_annotation(v[0])
        ann.label = k
        ann.has_default_value = v[1] != NOT_DATA
        inputs.append(ann)
    for k, v in node.preview_outputs().items():
        ann = parse_annotation(v)
        ann.label = k
        outputs.append(ann)

    return Metadata(
        node_type=NodeType.PYIRON_WORKFLOW_FUNCTION,
        python_import=f"{node.node_function.__module__}.{node.node_function.__qualname__}",
        category=f"{node.node_function.__module__}".replace(".", ">"),
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring=node.node_function.__doc__ or "",
        keywords=node.node_function.__module__.split("."),
        inputs=inputs,
        outputs=outputs,
    )
