import asyncio
import contextlib
import json
from http import HTTPStatus

import httpx2
import pytest

from sim_atlas_toolkit import orchestrator
from sim_atlas_toolkit.http_node_store import HttpNodeStore
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


class _ClosingMockNodeStore(MockNodeStore):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def test_upload_modules_leaves_caller_supplied_store_open() -> None:
    store = _ClosingMockNodeStore()

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"], store=store)

    assert not store.closed


def test_upload_modules_closes_store_it_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[_ClosingMockNodeStore] = []

    def make_store(api_url: str, api_key: str) -> _ClosingMockNodeStore:
        created.append(store := _ClosingMockNodeStore())
        return store

    monkeypatch.setattr(orchestrator, "HttpNodeStore", make_store)

    upload_modules(ToolkitSettings(), modules=["tests.test_orchestrator"])

    (store,) = created
    assert store.uploaded
    assert store.closed


def test_upload_modules_runs_store_requests_concurrently() -> None:
    """With ``concurrency=N`` the objects of a module are uploaded in
    parallel: N requests are in flight at the same time over HTTP."""
    n = 3
    in_flight = 0
    peak = 0
    all_in_flight = asyncio.Event()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        if in_flight == n:
            all_in_flight.set()
        try:
            # Hold each request open until N overlap. A store that serialises
            # requests never gets there; the timeout only keeps it from hanging.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(all_in_flight.wait(), timeout=1)
        finally:
            in_flight -= 1
        if request.method == "GET":
            return httpx2.Response(HTTPStatus.NOT_FOUND)
        body = json.loads(request.content)
        return httpx2.Response(
            HTTPStatus.CREATED,
            json={
                **body,
                "id": body.get("id") or body["hash"],
                "creator_name": "test",
                "creator_email": "test@example.com",
                "creation_timestamp": "2026-01-01T00:00:00+00:00",
            },
        )

    store = HttpNodeStore(
        "http://atlas.test/api", "secret", transport=httpx2.MockTransport(handler)
    )

    try:
        [summary] = upload_modules(
            ToolkitSettings(embed=False),
            modules=["tests.concurrency_module"],
            concurrency=n,
            store=store,
        )
    finally:
        asyncio.run(store.aclose())

    assert peak == n
    assert summary.errors == 0
    assert summary.created == n
