import inspect
import types
from typing import Annotated, Any, Union, get_args, get_origin

from griffe import (
    Docstring,
    DocstringSectionAttributes,
    DocstringSectionParameters,
    DocstringSectionReturns,
    DocstringSectionText,
    GoogleOptions,
    NumpyOptions,
    PerStyleOptions,
    SphinxOptions,
    parse_auto,
)
from pydantic import BaseModel

from sim_atlas_toolkit.models import Annotation, ArtifactType


class Reference(BaseModel):
    label: str
    obj: Any | None = None


class Metadata(BaseModel):
    artifact_type: ArtifactType

    name: str
    category: str

    python_import: str
    source_code: str

    keywords: list[str] = []

    docstring: str | None = None
    brief_description: str | None = None
    description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    children: list[Reference] = []


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
    metadata: Metadata,
) -> Metadata:
    """Fill Annotation.description from a parsed docstring; existing values are not overwritten."""
    if not docstring:
        return metadata
    sections = parse_auto(Docstring(docstring), per_style_options=_SILENCE)
    for section in sections:
        match section:
            case DocstringSectionParameters() | DocstringSectionAttributes():
                by_label = {a.label: a for a in metadata.inputs if a.label}
                for p in section.value:
                    ann = by_label.get(p.name)
                    if ann is not None and ann.description is None and p.description:
                        ann.description = p.description
            case DocstringSectionReturns():
                for i, ret in enumerate(section.value):
                    if (
                        i < len(metadata.outputs)
                        and metadata.outputs[i].description is None
                        and ret.description
                    ):
                        metadata.outputs[i].description = ret.description
            case DocstringSectionText():
                brief, _, long = section.value.partition("\n\n")
                if metadata.brief_description is None:
                    metadata.brief_description = brief.strip()
                if metadata.description is None:
                    metadata.description = long.strip()
            case _:
                pass
    return metadata


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


def parse_signature(sig: inspect.Signature) -> list[Annotation]:
    arguments: list[Annotation] = []
    for param_name, param in sig.parameters.items():
        ann = parse_annotation(param.annotation)
        ann.label = param_name
        arguments.append(ann)
    return arguments


def parse_return_annotation(sig: inspect.Signature) -> list[Annotation]:
    annotation = sig.return_annotation

    origin = get_origin(annotation)
    args = get_args(annotation)

    # unpack one level of Annotated
    if origin is Annotated:
        origin = get_origin(args[0])
        args = get_args(args[0])

    if origin is tuple:
        annotations: list[Annotation] = []
        for i, arg in enumerate(args):
            ann = parse_annotation(arg)
            ann.label = ann.label if ann.label is not None else str(i)
            annotations.append(ann)
        return annotations

    ann = parse_annotation(annotation)
    if not ann.label:
        ann.label = "return"
    return [ann]
