import inspect
from typing import Annotated, get_args, get_origin

from pydantic import BaseModel

from node_store_tools.models import Annotation


class FunctionMetadata(BaseModel):
    docstring: str | None
    arguments: dict[str, Annotation | None] | None
    returns: Annotation | None
    returns_unpacked: dict[str, Annotation | None] | None


def parse_annotation(annotation) -> Annotation:
    """Parse a type annotation to extract datatype, unit, and quantity.

    Args:
        annotation: The type annotation to parse.

    Returns:
        Annotation: The parsed annotation details.
    """

    from typing import get_args, get_origin

    if annotation is None:
        return Annotation()

    def get_name(obj):
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


def _parse_arguments(sig: inspect.Signature) -> dict[str, Annotation | None]:
    arguments = {}
    for param_name, param in sig.parameters.items():
        arguments[param_name] = (
            parse_annotation(param.annotation)
            if param.annotation != inspect.Parameter.empty
            else None
        )
    return arguments


def _parse_and_unpack_annotation(annotation) -> dict[str, Annotation | None]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    # unpack one level of Annotated
    if origin is Annotated:
        origin = get_origin(args[0])
        args = get_args(args[0])

    if origin is tuple:
        annotations = {}
        args = get_args(annotation)
        for i, arg in enumerate(args):
            ann = parse_annotation(arg)
            annotations[ann.label if ann.label is not None else str(i)] = ann
        return annotations

    return {}


def get_function_metadata(func: callable) -> FunctionMetadata:
    """Extract metadata from a function including its docstring, arguments, and return types.

    Args:
        func (callable): The function to extract metadata from.

    Returns:
        FunctionMetadata: The extracted metadata.
    """

    sig = inspect.signature(func)
    arguments = _parse_arguments(sig)

    return_annotation = sig.return_annotation
    returns = (
        parse_annotation(return_annotation)
        if return_annotation != inspect.Signature.empty
        else None
    )

    returns_unpacked = _parse_and_unpack_annotation(return_annotation)

    return FunctionMetadata(
        docstring=inspect.getdoc(func),
        arguments=arguments,
        returns=returns,
        returns_unpacked=returns_unpacked,
    )
