import hashlib
import inspect
import textwrap
from typing import Annotated, Any, get_args, get_origin

from node_store_spec.models import Annotation, NodeType

from .metadata import Metadata, _parse_annotation


def _parse_arguments(sig: inspect.Signature) -> list[Annotation]:
    arguments: list[Annotation] = []
    for param_name, param in sig.parameters.items():
        ann = (
            _parse_annotation(param.annotation)
            if param.annotation != inspect.Parameter.empty
            else Annotation()
        )
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
            ann = _parse_annotation(arg)
            ann.label = ann.label if ann.label is not None else str(i)
            annotations.append(ann)
        return annotations

    ann = _parse_annotation(annotation)
    if not ann.label:
        ann.label = "return"
    return [ann]


def parse(obj: Any) -> Metadata | None:
    if not (inspect.isfunction(obj) or inspect.isbuiltin(obj)):
        return None

    source_code = inspect.getsource(obj)
    source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    sig = inspect.signature(obj)
    inputs = _parse_arguments(sig)

    return_annotation = sig.return_annotation
    outputs = _parse_and_unpack_annotation(return_annotation)

    return Metadata(
        node_type=NodeType.FUNCTION,
        python_import=f"{obj.__module__}.{obj.__qualname__}",
        category=f"{obj.__module__}.{obj.__qualname__}".replace(".", ">"),
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring=inspect.getdoc(obj) or "",
        keywords=obj.__module__.split("."),
        inputs=inputs,
        outputs=outputs,
    )
