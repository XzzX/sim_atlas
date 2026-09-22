import inspect

import pytest

from sim_atlas_toolkit.models import ArtifactRequest, FunctionRequest, PackageRef
from sim_atlas_toolkit.parsers import python_function
from sim_atlas_toolkit.parsers.python_function import parse
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import install_mock_node_store


def _stub_provenance(*refs: PackageRef):
    """Replace the real environment lookup with fixed packages."""

    def apply(metadata: ArtifactRequest, _module_name: str | None) -> None:
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

    assert isinstance(artifact, FunctionRequest)

    assert artifact.name == "tests.test_python_function.simple"
    # enrich_from_docstring parsed the existing NumPy docstring.
    assert artifact.brief_description == "A simple function."
    assert artifact.inputs[0].description == "The first value."


def _double(z: int) -> int:
    return z * 2


def calls_helper(x: int) -> int:
    """Calls a module-level helper.

    Parameters
    ----------
    x : int
        The value to double.
    """
    return _double(x)


def references_missing_name(x: int) -> int:
    """Uses a name that resolves to nothing.

    Parameters
    ----------
    x : int
        The value to offset.
    """
    return x + undefined_global  # noqa: F821  # pyright: ignore[reportUndefinedVariable, reportUnknownVariableType] -- deliberately unresolved, to exercise the extractor's fallback


async def test_parse_self_contained_source_inlines_helper(
    monkeypatch: pytest.MonkeyPatch,
):
    store = install_mock_node_store(monkeypatch)
    settings = ToolkitSettings(self_contained_source=True)

    await parse(settings, calls_helper)

    artifact = store.uploaded[0]
    assert "def _double" in artifact.source_code
    assert "def calls_helper" in artifact.source_code
    # Docstring generation still ran off the plain (non-inlined) source.
    assert artifact.brief_description == "Calls a module-level helper."


async def test_parse_self_contained_source_falls_back_when_incomplete(
    monkeypatch: pytest.MonkeyPatch,
):
    store = install_mock_node_store(monkeypatch)
    settings = ToolkitSettings(self_contained_source=True)

    await parse(settings, references_missing_name)

    artifact = store.uploaded[0]
    # Falls back to the plain function source rather than emitting incomplete code.
    assert artifact.source_code == inspect.getsource(references_missing_name)


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
