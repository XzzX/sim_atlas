from sim_atlas_toolkit.models import FunctionRequest
from sim_atlas_toolkit.parsers.python_function import parse

from .mock_api import NodeStoreAPI


def simple(x: int, y: float) -> str:
    """A simple function.

    Parameters
    ----------
    x : int
        The first value.
    y : float
        The second value.

    Returns
    -------
    str
        The sum of ``x`` and ``y`` converted to a string.
    """
    return str(x + y)


def test_parse_simple_function():
    # Parse the function
    ns = NodeStoreAPI()
    responses = parse(simple, ns)  # pyright: ignore[reportArgumentType]
    assert len(responses) == 1
    assert len(ns.uploaded) == 1
    artifact = ns.uploaded[0]

    assert isinstance(artifact, FunctionRequest)

    assert artifact.name == "tests.test_python_function.simple"
