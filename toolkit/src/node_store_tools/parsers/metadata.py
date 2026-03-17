from typing import Annotated, Any, get_args, get_origin

from pydantic import BaseModel

from ..models import Annotation, NodeType


class Metadata(BaseModel):
    node_type: NodeType
    category: str

    python_import: str | None
    source_code: str
    source_code_hash: str

    keywords: list[str]

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


def _parse_annotation(annotation: Any) -> Annotation:
    """Parse a type annotation to extract datatype, unit, and quantity.

    Args:
        annotation: The type annotation to parse.

    Returns:
        Annotation: The parsed annotation details.
    """
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
            annotation.label = arg.get("label", annotation.label)
            annotation.unit = arg.get("unit", annotation.unit)
            annotation.quantity = arg.get("quantity", annotation.quantity)
    return annotation
