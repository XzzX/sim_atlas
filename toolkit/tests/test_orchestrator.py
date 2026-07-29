import httpx
import pytest

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.orchestrator import upload_modules
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import install_mock_node_store


def simple(x: int, y: float) -> str:
    """A simple function."""
    return str(x + y)


def test_upload_modules_triggers_embed_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"])

    assert store.embed_triggers == 1


def test_upload_modules_embed_disabled_skips_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)

    upload_modules(
        ToolkitSettings(embed_enabled=False), modules=["tests.test_orchestrator"]
    )

    assert store.embed_triggers == 0


def test_upload_modules_embed_not_configured_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = install_mock_node_store(monkeypatch)

    async def trigger_embed(api_url: str, api_key: str | None) -> httpx.Response:
        return httpx.Response(503)

    monkeypatch.setattr(node_store_api, "trigger_embed", trigger_embed)

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"])

    assert store.embed_triggers == 0
