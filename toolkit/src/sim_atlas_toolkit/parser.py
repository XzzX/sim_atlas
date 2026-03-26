from collections.abc import Callable
from typing import Any

from .parsers import (
    pyiron_core,
    pyiron_workflow,
    python_function,
    python_workflow_definition,
)
from .parsers.metadata import Metadata


def get_metadata(
    obj: Any, parsers: list[Callable[[Any], Metadata | None]] | None
) -> Metadata:
    if parsers is None:
        parsers = [
            pyiron_workflow.parse,
            pyiron_core.parse,
            python_workflow_definition.parse,
            python_function.parse,
        ]

    for parser in parsers:
        if metadata := parser(obj):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
