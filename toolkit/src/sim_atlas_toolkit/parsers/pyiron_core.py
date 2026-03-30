import hashlib
import inspect
from typing import Any

from ..models import Annotation, NodeType
from .metadata import Metadata


def parse(obj: Any) -> Metadata | None:
    if not hasattr(obj, "__globals__"):
        return None
    if obj.__globals__["__name__"] != "pyiron_core.pyiron_workflow.simple_workflow":
        return None

    source_code = inspect.getsource(obj)
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    instance = obj()

    inputs = [Annotation(label=k, datatype=v.type) for k, v in instance.inputs.items()]
    outputs = [
        Annotation(label=k, datatype=v.type) for k, v in instance.outputs.items()
    ]

    return Metadata(
        node_type=NodeType.PYIRON_CORE_NODE,
        python_import=f"{instance._func.__module__}.{instance._func.__qualname__}",
        category=f"{instance._func.__module__}".replace(".", ">"),
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring=instance._func.__doc__ or "",
        keywords=instance._func.__module__.split("."),
        inputs=inputs,
        outputs=outputs,
    )
