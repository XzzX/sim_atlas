import contextlib
import importlib
import importlib.metadata
import inspect
import logging
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

from sim_atlas_toolkit.models import (
    Annotation,
    ArtifactRequest,
)
from sim_atlas_toolkit.settings import EnrichmentSettings

logger = logging.getLogger(__name__)


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
    metadata: ArtifactRequest,
) -> ArtifactRequest:
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
                brief, _, _ = section.value.partition("\n\n")
                if metadata.brief_description is None:
                    metadata.brief_description = brief.strip()
                if metadata.description is None:
                    metadata.description = section.value
            case _:
                pass
    return metadata


async def enrich_metadata(
    metadata: ArtifactRequest, settings: EnrichmentSettings | None
) -> ArtifactRequest:
    """Optionally LLM-generate a docstring from the source, then enrich via griffe.

    When ``settings`` enables enrichment, a docstring is generated from
    ``metadata.source_code`` and stored on ``metadata.docstring`` before it is
    parsed by griffe. Without enrichment this behaves like ``enrich_from_docstring``.
    """
    docstring = metadata.docstring or ""
    should_generate = (
        settings is not None
        and settings.enabled
        and bool(metadata.source_code)
        and (settings.overwrite or not docstring)
    )
    if should_generate:
        assert settings is not None
        try:
            from sim_atlas_toolkit.parsers.ai_enrichment import (  # noqa: PLC0415
                generate_docstring,
            )

            generated = await generate_docstring(
                settings.url, settings.key, settings.model, metadata.source_code
            )
            if generated:
                docstring = generated
                metadata.docstring = generated
        except Exception:
            logger.exception("LLM docstring generation failed for %s", metadata.name)
    enrich_from_docstring(docstring, metadata)
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


def extract_module_metadata(
    module: types.ModuleType, metadata: ArtifactRequest
) -> ArtifactRequest:
    package_name = module.__name__.partition(".")[0]

    with contextlib.suppress(Exception):
        if dependencies := importlib.metadata.requires(package_name):
            metadata.dependencies = dependencies

    with contextlib.suppress(Exception):
        package_metadata = importlib.metadata.metadata(package_name).json

        if author := package_metadata.get("author"):
            metadata.author_name = author if isinstance(author, str) else author[0]
        if email := package_metadata.get("author_email"):
            metadata.author_email = email if isinstance(email, str) else email[0]
        if project_url := package_metadata.get("project_url"):
            for item in project_url:
                key, url = item.split(", ")
                match key.lower():
                    case "homepage":
                        metadata.homepage_url = url
                    case "documentation":
                        metadata.documentation_url = url
                    case "source" | "code" | "repository" | "github":
                        metadata.source_url = url
                    case _:
                        pass

    return metadata
