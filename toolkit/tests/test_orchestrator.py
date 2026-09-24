from sim_atlas_toolkit.orchestrator import upload_modules
from sim_atlas_toolkit.settings import ToolkitSettings

from .mock_api import MockNodeStore


def simple(x: int, y: float) -> str:
    """A simple function."""
    return str(x + y)


def test_upload_modules_triggers_embed_by_default() -> None:
    store = MockNodeStore()

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"], store=store)

    assert store.embed_triggers == 1


def test_upload_modules_embed_disabled_skips_trigger() -> None:
    store = MockNodeStore()

    upload_modules(
        ToolkitSettings(embed=False), modules=["tests.test_orchestrator"], store=store
    )

    assert store.embed_triggers == 0


def test_upload_modules_embed_not_configured_does_not_raise() -> None:
    store = MockNodeStore()
    store.embed_available = False

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"], store=store)

    assert store.embed_triggers == 0


def test_upload_modules_reports_existing_not_errors() -> None:
    """Regression test for the dedup-counted-as-error bug: uploading the same
    module twice must report the second pass's hits as ``existing``, not
    ``errors``."""
    store = MockNodeStore()

    first = upload_modules(
        ToolkitSettings(), modules=["tests.test_orchestrator"], store=store
    )
    second = upload_modules(
        ToolkitSettings(), modules=["tests.test_orchestrator"], store=store
    )

    assert first[0].created > 0
    assert first[0].errors == 0
    assert second[0].created == 0
    assert second[0].existing == first[0].created
    assert second[0].errors == 0
