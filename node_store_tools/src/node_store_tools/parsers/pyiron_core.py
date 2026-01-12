from typing import Any

from node_store_spec.models import Annotation, NodeType

from .metadata import Metadata


def parse(obj: Any) -> Metadata | None:
    if obj.__globals__["__name__"] != "pyiron_core.pyiron_workflow.simple_workflow":
        return None

    import hashlib
    import inspect

    source_code = inspect.getsource(obj)
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    instance = obj()

    inputs = {}
    for k, v in instance.inputs.items():
        inputs[k] = Annotation(label=k, datatype=v.type)

    outputs = {}
    for k, v in instance.outputs.items():
        outputs[k] = Annotation(label=k, datatype=v.type)

    return Metadata(
        source_code=source_code,
        source_code_hash=source_code_hash,
        inputs=inputs,
        outputs=outputs,
        node_type=NodeType.PYIRON_CORE_NODE,
    )
