import inspect
from typing import Any

from .parsers.metadata import Metadata
from .parsers.python_function import get_function_metadata


def create_parser_mapping() -> dict[type, Any]:
    """Create a mapping of object types to their corresponding parser functions.

    Returns:
        dict[type, Any]: A dictionary mapping object types to parser functions.
    """
    parsers = {}

    try:
        from .parsers import python_workflow_definition

        parsers.update(python_workflow_definition.parsers)
    except ImportError:
        pass

    try:
        from .parsers import pyiron_workflow

        parsers.update(pyiron_workflow.parsers)
    except ImportError:
        pass

    return parsers


parsers = create_parser_mapping()


def get_metadata(obj: Any) -> Metadata:
    """Extract metadata from a function including its docstring, arguments, and return
    types.

    Args:
        func (callable): The function to extract metadata from.

    Returns:
        FunctionMetadata: The extracted metadata.
    """

    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return get_function_metadata(obj)

    for obj_type, parser_func in parsers.items():
        if isinstance(obj, type):
            if issubclass(obj, obj_type):
                return parser_func(obj)
        else:
            if isinstance(obj, obj_type):
                return parser_func(obj)

    raise ValueError(f"No parser available for the given object type: {type(obj)}")
