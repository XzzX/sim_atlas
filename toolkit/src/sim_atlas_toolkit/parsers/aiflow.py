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

from __future__ import annotations

import inspect
import textwrap
import uuid
from dataclasses import MISSING, fields, is_dataclass, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _type_to_str(tp: Any) -> str:
    if tp is None:
        return "None"
    if isinstance(tp, str):
        return tp
    if getattr(tp, "__module__", None) == "builtins":
        return getattr(tp, "__name__", str(tp))
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp).replace("typing.", "")


def _clean_docstring(obj: Any) -> str:
    return inspect.getdoc(obj) or ""


def _get_source_code(obj: Any) -> str:
    try:
        return textwrap.dedent(inspect.getsource(obj))
    except Exception:
        return ""


def _module_rel(obj: Any, root_path: str | Path | None = None) -> str:
    if root_path is not None:
        try:
            source_file = inspect.getsourcefile(obj)
            if source_file:
                rel_path = Path(source_file).resolve().relative_to(Path(root_path).resolve())
                return ".".join(rel_path.with_suffix("").parts)
        except Exception:
            pass
    return getattr(obj, "__module__", "") or ""


def _category_from_module(module_rel: str) -> str:
    parts = module_rel.split(".")
    if len(parts) <= 1:
        return module_rel
    return ">".join(parts[:-1])


def _full_name(module_rel: str, cls_name: str) -> str:
    return f"{module_rel}.{cls_name}" if module_rel else cls_name


def _unwrap_original_dataclass(obj: Any) -> tuple[Any, str]:
    """
    Returns (original_dataclass_class, direction)

    direction:
      - "input"  for @as_inp_dataclass_node
      - "output" for @as_out_dataclass_node
      - "plain"  for undecorated dataclass
    """
    if hasattr(obj, "_is_inp_dataclass_node") and getattr(obj, "_is_inp_dataclass_node"):
        return obj._original_dataclass, "input"

    if hasattr(obj, "_original_dataclass"):
        return obj._original_dataclass, "output"

    return obj, "plain"


def _extract_input_ports_from_dataclass(cls: Any) -> list[dict[str, Any]]:
    result = []
    for f in fields(cls):
        has_default = not (f.default is MISSING and getattr(f, "default_factory", MISSING) is MISSING)
        entry = {
            "has_default_value": has_default,
            "label": f.name,
            "datatype": _type_to_str(f.type),
            "unit": None,
            "quantity": None,
            "description": None,
        }
        if f.default is not MISSING:
            entry["default_value"] = f.default
        elif getattr(f, "default_factory", MISSING) is not MISSING:
            try:
                entry["default_value"] = f.default_factory()
            except Exception:
                entry["default_value"] = None
        result.append(entry)
    return result


def _extract_output_ports_from_dataclass(cls: Any) -> list[dict[str, Any]]:
    return [
        {
            "has_default_value": False,
            "label": f.name,
            "datatype": _type_to_str(f.type),
            "unit": None,
            "quantity": None,
            "description": None,
        }
        for f in fields(cls)
    ]


def convert_dataclass_node_to_artifact(
    wrapped: Any,
    *,
    root_path: str | Path | None = None,
    artifact_id: str | None = None,
    author_name: str | None = None,
    author_email: str | None = None,
    creator_name: str | None = None,
    creator_email: str | None = None,
    creation_timestamp: str | None = None,
    homepage_url: str | None = None,
    documentation_url: str | None = None,
    source_url: str | None = None,
    keywords: list[str] | None = None,
    brief_description: str = "",
    description: str = "",
) -> dict[str, Any]:
    original_cls, direction = _unwrap_original_dataclass(wrapped)

    if not is_dataclass(original_cls):
        try:
            original_cls = dataclass(original_cls)
        except Exception as exc:
            raise TypeError(f"Object is not a dataclass or dataclass-node: {wrapped!r}") from exc

    module_rel = _module_rel(original_cls, root_path=root_path)
    cls_name = original_cls.__name__
    full_name = _full_name(module_rel, cls_name)

    if direction == "input":
        inputs = _extract_input_ports_from_dataclass(original_cls)
        outputs = [
            {
                "has_default_value": False,
                "label": "output",
                "datatype": cls_name,
                "unit": None,
                "quantity": None,
                "description": None,
            }
        ]
    elif direction == "output":
        inputs = [
            {
                "has_default_value": False,
                "label": "input",
                "datatype": cls_name,
                "unit": None,
                "quantity": None,
                "description": None,
            }
        ]
        outputs = _extract_output_ports_from_dataclass(original_cls)
    else:
        inputs = _extract_input_ports_from_dataclass(original_cls)
        outputs = []

    return {
        "artifact_type": "dataclass",
        "dataclass_role": direction,
        "id": artifact_id or str(uuid.uuid4()),
        "name": full_name,
        "category": _category_from_module(module_rel),
        "keywords": keywords or [],
        "author_name": author_name,
        "author_email": author_email,
        "creator_name": creator_name or author_name,
        "creator_email": creator_email or author_email,
        "creation_timestamp": creation_timestamp or datetime.now(timezone.utc).isoformat(),
        "homepage_url": homepage_url,
        "documentation_url": documentation_url,
        "source_url": source_url,
        "python_import": full_name,
        "dependencies": None,
        "source_code": _get_source_code(original_cls),
        "docstring": _clean_docstring(original_cls),
        "brief_description": brief_description,
        "description": description,
        "inputs": inputs,
        "outputs": outputs,
    }