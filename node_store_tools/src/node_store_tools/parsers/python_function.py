import inspect
from typing import Annotated, Any, get_args, get_origin

from node_store_spec.models import Annotation, NodeType

from .metadata import Metadata


def _parse_annotation(annotation: Any) -> Annotation:
    """Parse a type annotation to extract datatype, unit, and quantity.

    Args:
        annotation: The type annotation to parse.

    Returns:
        Annotation: The parsed annotation details.
    """

    from typing import get_args, get_origin

    if annotation is None:
        return Annotation()

    def get_name(obj: Any) -> str:
        return obj.__name__ if hasattr(obj, "__name__") else obj.__class__.__name__

    origin = get_origin(annotation)
    if origin is not Annotated:
        return Annotation(datatype=get_name(annotation))

    args = get_args(annotation)
    annotation = Annotation(datatype=get_name(args[0]))
    for arg in args[1:]:
        if isinstance(arg, dict):
            annotation.label = arg.get("label", annotation.unit)
            annotation.unit = arg.get("unit", annotation.unit)
            annotation.quantity = arg.get("quantity", annotation.quantity)
    return annotation


def _parse_arguments(sig: inspect.Signature) -> dict[str, Annotation]:
    arguments: dict[str, Annotation] = {}
    for param_name, param in sig.parameters.items():
        arguments[param_name] = (
            _parse_annotation(param.annotation)
            if param.annotation != inspect.Parameter.empty
            else Annotation()
        )
    return arguments


def _parse_and_unpack_annotation(annotation: Any) -> dict[str, Annotation]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    # unpack one level of Annotated
    if origin is Annotated:
        origin = get_origin(args[0])
        args = get_args(args[0])

    if origin is tuple:
        annotations: dict[str, Annotation] = {}
        args = get_args(annotation)
        for i, arg in enumerate(args):
            ann = _parse_annotation(arg)
            annotations[ann.label if ann.label is not None else str(i)] = ann
        return annotations

    return {}


def parse(obj: Any) -> Metadata | None:
    if not (inspect.isfunction(obj) or inspect.ismethod(obj)):
        return None

    import hashlib
    import textwrap

    source_code = inspect.getsource(obj)
    source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))
    source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

    sig = inspect.signature(obj)
    inputs = _parse_arguments(sig)

    return_annotation = sig.return_annotation
    outputs = _parse_and_unpack_annotation(return_annotation)

    return Metadata(
        node_type=NodeType.FUNCTION,
        source_code=source_code,
        source_code_hash=source_code_hash,
        docstring=inspect.getdoc(obj),
        inputs=inputs,
        outputs=outputs,
    )
