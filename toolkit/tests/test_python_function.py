import pytest

from sim_atlas_toolkit.models import ArtifactType, NodeRequest, PackageRef
from sim_atlas_toolkit.parsers import python_function
from sim_atlas_toolkit.parsers.python_function import parse
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import install_mock_node_store


def _stub_provenance(*refs: PackageRef):
    """Replace the real environment lookup with fixed packages."""

    def apply(metadata: NodeRequest, _module_name: str | None) -> None:
        metadata.packages = list(refs)

    return apply


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

    assert artifact.artifact_type == ArtifactType.FUNCTION

    assert artifact.name == "tests.test_python_function.simple"
    # enrich_from_docstring parsed the existing NumPy docstring.
    assert artifact.brief_description == "A simple function."
    assert artifact.inputs[0].description == "The first value."


async def test_parse_attaches_package_provenance(monkeypatch: pytest.MonkeyPatch):
    """The parser records which distribution the function came from."""
    ref = PackageRef(
        ecosystem="conda", name="demo", version="1.0", channel="conda-forge"
    )
    monkeypatch.setattr(
        python_function, "apply_provenance", _stub_provenance(ref), raising=True
    )
    store = install_mock_node_store(monkeypatch)

    await parse(ToolkitSettings(), simple)

    assert store.uploaded[0].packages == [ref]
