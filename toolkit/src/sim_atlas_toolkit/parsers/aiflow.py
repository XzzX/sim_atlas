# pyright: basic
from __future__ import annotations

import inspect
import textwrap
from typing import Any

from ..models import Annotation, ArtifactType
from .metadata import (
    Metadata,
    enrich_from_docstring,
    parse_return_annotation,
    parse_signature,
)

try:
    from core.node import FunctionNode  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    FunctionNode = None


def _is_aiflow_node(obj: Any) -> bool:
    if hasattr(obj, "_original_func"):
        return True
    if FunctionNode is not None:
        if inspect.isclass(obj) and issubclass(obj, FunctionNode):
            return True
        if isinstance(obj, FunctionNode):
            return True
    return False


def _resolve_func(wrapped: Any) -> tuple[Any, Any]:
    """Resolve the underlying function and optionally a node instance."""
    node_instance = None
    func = None

    if hasattr(wrapped, "_original_func"):
        func = wrapped._original_func
    elif hasattr(wrapped, "func"):
        func = wrapped.func
        node_instance = wrapped
    elif FunctionNode is not None and inspect.isclass(wrapped) and issubclass(wrapped, FunctionNode):
        node_instance = wrapped()
        func = node_instance.func
    elif callable(wrapped):
        func = wrapped
    else:
        raise TypeError(f"Unsupported object type: {type(wrapped)!r}")

    if func is None:
        raise ValueError("Could not resolve original function.")

    if node_instance is None and inspect.isclass(wrapped):
        try:
            node_instance = wrapped()
        except Exception:
            node_instance = None

    return func, node_instance


def parse(obj: Any) -> list[Metadata]:
    if not _is_aiflow_node(obj):
        return []

    try:
        func, node_instance = _resolve_func(obj)
    except (TypeError, ValueError):
        return []

    try:
        source_code = textwrap.dedent(inspect.getsource(func).replace("\r\n", ""))
    except OSError:
        return []

    sig = inspect.signature(func)
    inputs = parse_signature(sig)
    for ann, param in zip(inputs, sig.parameters.values(), strict=False):
        ann.has_default_value = param.default is not inspect.Parameter.empty

    if node_instance is not None and hasattr(node_instance, "outputs") and hasattr(node_instance.outputs, "ports"):
        port_names = list(node_instance.outputs.ports.keys())
        return_anns = parse_return_annotation(sig)
        outputs: list[Annotation] = []
        for i, name in enumerate(port_names):
            ann = return_anns[i] if i < len(return_anns) else Annotation()
            ann.label = name
            outputs.append(ann)
    else:
        outputs = parse_return_annotation(sig)

    module = getattr(func, "__module__", "") or ""
    qualname = getattr(func, "__qualname__", func.__name__)

    metadata = Metadata(
        name=f"{module}.{qualname}",
        artifact_type=ArtifactType.FUNCTION,
        python_import=f"{module}.{qualname}",
        category=module.replace(".", ">"),
        source_code=source_code,
        docstring=inspect.getdoc(func) or "",
        keywords=[],
        inputs=inputs,
        outputs=outputs,
    )

    enrich_from_docstring(inspect.getdoc(func) or "", metadata)

    return [metadata]