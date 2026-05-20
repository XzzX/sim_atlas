import inspect
import textwrap
from typing import Annotated, Any, get_args, get_origin

from ..models import Annotation, NodeType
from .metadata import Metadata, parse_annotation


def _parse_arguments(sig: inspect.Signature) -> list[Annotation]:
    arguments: list[Annotation] = []
    for param_name, param in sig.parameters.items():
        ann = parse_annotation(param.annotation)
        ann.label = param_name
        arguments.append(ann)
    return arguments


def _parse_and_unpack_annotation(annotation: Any) -> list[Annotation]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    # unpack one level of Annotated
    if origin is Annotated:
        origin = get_origin(args[0])
        args = get_args(args[0])

    if origin is tuple:
        annotations: list[Annotation] = []
        args = get_args(annotation)
        for i, arg in enumerate(args):
            ann = parse_annotation(arg)
            ann.label = ann.label if ann.label is not None else str(i)
            annotations.append(ann)
        return annotations

    ann = parse_annotation(annotation)
    if not ann.label:
        ann.label = "return"
    return [ann]


def parse(obj: Any) -> list[Metadata]:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return []

    if inspect.isbuiltin(obj):
        source_code = f"{obj.__name__}{inspect.signature(obj)}"
    else:
        source_code = inspect.getsource(obj)
    source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))

    sig = inspect.signature(obj)
    inputs = _parse_arguments(sig)

    return_annotation = sig.return_annotation
    outputs = _parse_and_unpack_annotation(return_annotation)

    return [
        Metadata(
            name=f"{obj.__module__}.{obj.__qualname__}",
            node_type=NodeType.FUNCTION,
            python_import=f"{obj.__module__}.{obj.__qualname__}",
            category=f"{obj.__module__}".replace(".", ">"),
            source_code=source_code,
            docstring=inspect.getdoc(obj) or "",
            keywords=obj.__module__.split("."),
            inputs=inputs,
            outputs=outputs,
        )
    ]
