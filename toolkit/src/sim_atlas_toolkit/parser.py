from collections.abc import Callable
from typing import Any

from .parsers import (
    aiflow,
    dataclass_node,
    flowrep_parser,
    pyiron_core,
    pyiron_workflow,
    python_function,
    python_workflow_definition,
)
from .parsers.metadata import Metadata


def get_metadata(
    obj: Any, parsers: list[Callable[[Any], list[Metadata]]] | None
) -> list[Metadata]:
    if parsers is None:
        parsers = [
            aiflow.parse,
            dataclass_node.parse,
            pyiron_workflow.parse,
            pyiron_core.parse,
            python_workflow_definition.parse,
            flowrep_parser.parse,
            python_function.parse,
        ]

    for parser in parsers:
        if metadata := parser(obj):
            return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
