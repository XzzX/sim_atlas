from __future__ import annotations

import inspect
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, get_type_hints

try:
    from core.node import FunctionNode
except Exception:  # pragma: no cover
    FunctionNode = None


def _type_to_str(tp: Any) -> str:
    if tp is inspect.Signature.empty:
        return "Any"
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


def _get_source_code(func: Any) -> str:
    try:
        return textwrap.dedent(inspect.getsource(func))
    except Exception:
        return ""


def _module_rel_from_func(func: Any, root_path: str | Path | None = None) -> str:
    if root_path is not None:
        try:
            source_file = inspect.getsourcefile(func)
            if source_file:
                rel_path = Path(source_file).resolve().relative_to(Path(root_path).resolve())
                return ".".join(rel_path.with_suffix("").parts)
        except Exception:
            pass
    return getattr(func, "__module__", "") or ""


def _category_from_module(module_rel: str) -> str:
    parts = module_rel.split(".")
    if len(parts) <= 1:
        return module_rel
    return ">".join(parts[:-1])


def _artifact_name(module_rel: str, func_name: str) -> str:
    return f"{module_rel}.{func_name}" if module_rel else func_name


def _extract_output_labels(func_or_node: Any) -> list[str]:
    if hasattr(func_or_node, "outputs") and hasattr(func_or_node.outputs, "ports"):
        return list(func_or_node.outputs.ports.keys())
    return ["return"]


def convert_function_node_to_artifact(
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
    """
    Convert an @as_function_node-decorated function/class/instance into the
    structured artifact metadata format shown in the user example.
    """

    # Accept:
    # - original decorated class
    # - node instance
    # - wrapped function/class exposing _original_func
    node_instance = None
    func = None

    if hasattr(wrapped, "_original_func"):
        func = wrapped._original_func
    elif hasattr(wrapped, "func"):
        func = wrapped.func
        node_instance = wrapped
    elif inspect.isclass(wrapped) and FunctionNode is not None and issubclass(wrapped, FunctionNode):
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

    sig = inspect.signature(func)
    hints = get_type_hints(func)
    module_rel = _module_rel_from_func(func, root_path=root_path)
    func_name = func.__name__
    full_name = _artifact_name(module_rel, func_name)
    output_labels = _extract_output_labels(node_instance) if node_instance is not None else ["return"]

    inputs = []
    for param_name, param in sig.parameters.items():
        ann = hints.get(param_name, param.annotation)
        has_default = param.default is not inspect.Parameter.empty
        inputs.append(
            {
                "has_default_value": has_default,
                "label": param_name,
                "datatype": _type_to_str(ann),
                "unit": None,
                "quantity": None,
                "description": None,
                **({"default_value": param.default} if has_default else {}),
            }
        )

    return_ann = hints.get("return", sig.return_annotation)
    outputs = [
        {
            "has_default_value": False,
            "label": output_labels[0] if len(output_labels) == 1 else "return",
            "datatype": _type_to_str(return_ann),
            "unit": None,
            "quantity": None,
            "description": None,
        }
    ]

    return {
        "artifact_type": "function",
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
        "source_code": _get_source_code(func),
        "docstring": _clean_docstring(func),
        "brief_description": brief_description,
        "description": description,
        "inputs": inputs,
        "outputs": outputs,
    }