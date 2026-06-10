import inspect
import types
from typing import Annotated, Any, Union, get_args, get_origin

from griffe import (
    Docstring,
    DocstringSectionAttributes,
    DocstringSectionParameters,
    DocstringSectionReturns,
    GoogleOptions,
    NumpyOptions,
    PerStyleOptions,
    SphinxOptions,
    parse_auto,
)
from pydantic import BaseModel

from ..models import Annotation, ArtifactType


class Metadata(BaseModel):
    name: str | None = None
    artifact_type: ArtifactType
    category: str

    python_import: str | None
    source_code: str

    keywords: list[str]

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


def type_to_str(tp: Any) -> str:
    """Recursively convert a Python type annotation to a canonical string.

    Examples:
        int              -> "int"
        type(None)       -> "None"
        list[int]        -> "list[int]"
        dict[str, float] -> "dict[str, float]"
        int | float      -> "int | float"
        Optional[int]    -> "int | None"
    """
    if tp is type(None):
        return "None"

    origin = get_origin(tp)
    args = get_args(tp)

    # Union: PEP 604 (int | float) or typing.Union / Optional
    if origin is Union or isinstance(tp, types.UnionType):
        return " | ".join(type_to_str(a) for a in args)

    # Generic alias: list[int], dict[str, float], etc.
    if origin is not None and args:
        name = getattr(origin, "__name__", str(origin))
        return f"{name}[{', '.join(type_to_str(a) for a in args)}]"

    # Simple type
    return getattr(tp, "__name__", str(tp))


_SILENCE: PerStyleOptions = {
    "google": GoogleOptions(warn_unknown_params=False, warn_missing_types=False),
    "numpy": NumpyOptions(warnings=False),
    "sphinx": SphinxOptions(warnings=False),
}


def enrich_from_docstring(
    docstring: str,
    inputs: list[Annotation],
    outputs: list[Annotation],
) -> None:
    """Fill Annotation.description from a parsed docstring; existing values are not overwritten."""
    if not docstring:
        return
    sections = parse_auto(Docstring(docstring), per_style_options=_SILENCE)
    for section in sections:
        if isinstance(section, DocstringSectionParameters | DocstringSectionAttributes):
            by_label = {a.label: a for a in inputs if a.label}
            for p in section.value:
                ann = by_label.get(p.name)
                if ann is not None and ann.description is None and p.description:
                    ann.description = p.description
        elif isinstance(section, DocstringSectionReturns):
            for i, ret in enumerate(section.value):
                if (
                    i < len(outputs)
                    and outputs[i].description is None
                    and ret.description
                ):
                    outputs[i].description = ret.description


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
        return Annotation(datatype=type_to_str(annotation))

    args = get_args(annotation)
    result = Annotation(datatype=type_to_str(args[0]))
    for arg in args[1:]:
        if isinstance(arg, dict):
            result.label = arg.get("label", result.label)  # type: ignore
            result.unit = arg.get("unit", result.unit)  # type: ignore
            result.quantity = arg.get("quantity", result.quantity)  # type: ignore
            result.description = arg.get("description", result.description)  # type: ignore
    return result
