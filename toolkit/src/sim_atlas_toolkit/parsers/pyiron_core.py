import inspect
from typing import Any

from ..models import Annotation, ArtifactType
from .metadata import Metadata


def parse(obj: Any) -> list[Metadata]:
    if not hasattr(obj, "__globals__"):
        return []
    if obj.__globals__["__name__"] != "pyiron_core.pyiron_workflow.simple_workflow":
        return []

    source_code = inspect.getsource(obj)

    instance = obj()

    inputs = [Annotation(label=k, datatype=v.type) for k, v in instance.inputs.items()]
    outputs = [
        Annotation(label=k, datatype=v.type) for k, v in instance.outputs.items()
    ]

    return [
        Metadata(
            name=f"{instance._func.__module__}.{instance._func.__qualname__}",
            artifact_type=ArtifactType.FUNCTION,
            python_import=f"{instance._func.__module__}.{instance._func.__qualname__}",
            category=f"{instance._func.__module__}".replace(".", ">"),
            source_code=source_code,
            docstring=instance._func.__doc__ or "",
            keywords=instance._func.__module__.split("."),
            inputs=inputs,
            outputs=outputs,
        )
    ]
