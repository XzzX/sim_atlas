from typing import Any

from .parsers import (
    pyiron_core,
    pyiron_workflow,
    python_function,
    python_workflow_definition,
)
from .parsers.metadata import Metadata


def get_metadata(obj: Any) -> Metadata:
    """Extract metadata from a function including its docstring, arguments, and return
    types.

    Args:
        func (callable): The function to extract metadata from.

    Returns:
        FunctionMetadata: The extracted metadata.
    """

    if metadata := pyiron_workflow.parse(obj):
        return metadata
    if metadata := pyiron_core.parse(obj):
        return metadata
    if metadata := python_workflow_definition.parse(obj):
        return metadata
    if metadata := python_function.parse(obj):
        return metadata

    raise ValueError(f"No parser available for the given object: {type(obj)}")
