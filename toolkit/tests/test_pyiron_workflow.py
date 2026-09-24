import pytest

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.parsers import pyiron_workflow
from sim_atlas_toolkit.parsers.pyiron_workflow import parse, supports_legacy_api
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import MockNodeStore


@pytest.mark.parametrize("raw_version", ["0.15.6", "0.16.0", "0.17.0"])
def test_legacy_versions_are_supported(raw_version: str) -> None:
    assert supports_legacy_api(raw_version)


@pytest.mark.parametrize("raw_version", ["0.18.0", "0.19.1", "1.0.0", "unknown"])
def test_flowrep_based_versions_are_not_supported(raw_version: str) -> None:
    assert not supports_legacy_api(raw_version)


async def test_parse_ignores_non_types() -> None:
    store = MockNodeStore()
    assert await parse(ParseContext(ToolkitSettings(), store), 42) == []
    assert store.uploaded == []


async def test_parse_skips_unsupported_version(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MockNodeStore()
    monkeypatch.setattr(pyiron_workflow, "_legacy_api_available", lambda: False)

    class SomeNode:
        pass

    assert await parse(ParseContext(ToolkitSettings(), store), SomeNode) == []
    assert store.uploaded == []
