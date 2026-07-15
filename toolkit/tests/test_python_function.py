import pytest

from sim_atlas_toolkit.models import FunctionRequest
from sim_atlas_toolkit.parsers.python_function import parse
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import install_mock_node_store


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


async def test_parse_simple_function(monkeypatch: pytest.MonkeyPatch):
    # Parse the function
    store = install_mock_node_store(monkeypatch)
    responses = await parse(ToolkitSettings(), simple)
    assert len(responses) == 1
    assert len(store.uploaded) == 1
    artifact = store.uploaded[0]

    assert isinstance(artifact, FunctionRequest)

    assert artifact.name == "tests.test_python_function.simple"
