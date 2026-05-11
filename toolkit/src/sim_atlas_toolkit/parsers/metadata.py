import inspect
import types
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel

from ..models import Annotation, DataType, GenericNode, NodeType, SimpleNode, UnionNode


class Metadata(BaseModel):
    node_type: NodeType
    category: str

    python_import: str | None
    source_code: str

    keywords: list[str]

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


def _node_to_str(node: SimpleNode | GenericNode | UnionNode) -> str:
    if isinstance(node, SimpleNode):
        return node.name
    if isinstance(node, GenericNode):
        return f"{node.name}[{', '.join(_node_to_str(a) for a in node.args)}]"
    return " | ".join(_node_to_str(m) for m in node.members)


def _type_to_node(tp: Any) -> SimpleNode | GenericNode | UnionNode:
    """Recursively convert a Python type annotation to a TypeNode AST."""
    if tp is type(None):
        return SimpleNode(name="None")

    origin = get_origin(tp)
    args = get_args(tp)

    # Union: PEP 604 (int | float) or typing.Union / Optional
    if origin is Union or isinstance(tp, types.UnionType):
        return UnionNode(members=[_type_to_node(a) for a in args])

    # Generic alias: list[int], dict[str, float], etc.
    if origin is not None and args:
        name = getattr(origin, "__name__", str(origin))
        return GenericNode(name=name, args=[_type_to_node(a) for a in args])

    # Simple type
    return SimpleNode(name=getattr(tp, "__name__", str(tp)))


def _make_datatype(tp: Any) -> DataType:
    node = _type_to_node(tp)
    return DataType(ast=node, string=_node_to_str(node))


def parse_annotation(annotation: Any) -> Annotation:
    """Parse a type annotation to extract datatype, unit, and quantity.

    Args:
        annotation: The type annotation to parse.

    Returns:
        Annotation: The parsed annotation details.
    """
    if annotation is None:
        return Annotation()

    if annotation == inspect.Parameter.empty:
        return Annotation()

    origin = get_origin(annotation)
    if origin is not Annotated:
        return Annotation(datatype=_make_datatype(annotation))

    args = get_args(annotation)
    result = Annotation(datatype=_make_datatype(args[0]))
    for arg in args[1:]:
        if isinstance(arg, dict):
            result.label = arg.get("label", result.label)  # type: ignore
            result.unit = arg.get("unit", result.unit)  # type: ignore
            result.quantity = arg.get("quantity", result.quantity)  # type: ignore
    return result
