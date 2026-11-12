"""Behaviour of ``HttpNodeStore`` against a mocked backend.

Every request goes through ``httpx2.MockTransport``, so these tests also
prove the store sends its requests through the injected async transport
rather than through module-level (synchronous) ``httpx2`` calls.
"""

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import httpx2
import pytest
from pydantic import ValidationError
from sim_atlas_models import (
    AnnotationResponse,
    ArtifactType,
    ExecutionResultRequest,
    NodeRequest,
    ReferenceResponse,
    WfDefinition,
    WfFunctionNode,
)

from sim_atlas_toolkit.http_node_store import HttpNodeStore
from sim_atlas_toolkit.node_store import (
    EmbeddingNotConfiguredError,
    NodeStatus,
    NodeStoreError,
)

from .http_backend import http_backend

API_URL = "http://atlas.test/api"

Handler = (
    Callable[[httpx2.Request], httpx2.Response]
    | Callable[[httpx2.Request], Coroutine[Any, Any, httpx2.Response]]
)


def _node_request(name: str = "f") -> NodeRequest:
    return NodeRequest(
        artifact_type=ArtifactType.FUNCTION,
        hash=f"hash-{name}",
        name=name,
        category="test",
        keywords=[],
        source_code="def f(): ...",
        inputs=[],
        outputs=[],
    )


def _node_response_json(name: str = "f") -> dict[str, Any]:
    return {
        **_node_request(name).model_dump(mode="json"),
        "id": f"id-{name}",
        "creator_name": "test",
        "creator_email": "test@example.com",
        "creation_timestamp": datetime.now(UTC).isoformat(),
    }


def _execution_result_request() -> ExecutionResultRequest:
    return ExecutionResultRequest(
        author_name="a",
        author_email="a@example.com",
        artifact_id="id-f",
        inputs=[],
        outputs="42",
    )


def _execution_result_response_json() -> dict[str, Any]:
    return {
        **_execution_result_request().model_dump(mode="json"),
        "id": "exec-1",
        "creator_name": "test",
        "creator_email": "test@example.com",
        "creation_timestamp": datetime.now(UTC).isoformat(),
    }


def _store(handler: Handler, api_key: str = "secret") -> HttpNodeStore:
    return HttpNodeStore(API_URL, api_key, transport=httpx2.MockTransport(handler))


def _respond(status: int, body: Any = None) -> Handler:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json=body)

    return handler


# --- create_node ---------------------------------------------------------


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (HTTPStatus.CREATED, NodeStatus.CREATED),
        (HTTPStatus.CONFLICT, NodeStatus.EXISTS),
    ],
)
async def test_create_node_maps_status_to_node_status(
    status_code: int, expected: NodeStatus
) -> None:
    async with _store(_respond(status_code, _node_response_json())) as store:
        result = await store.create_node(_node_request())

    assert result.status is expected
    assert result.node.id == "id-f"


@pytest.mark.parametrize(
    "status_code",
    [HTTPStatus.OK, HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY, 500],
)
async def test_create_node_raises_on_other_status(status_code: int) -> None:
    async with _store(_respond(status_code, _node_response_json())) as store:
        with pytest.raises(NodeStoreError):
            await store.create_node(_node_request())


async def test_create_node_posts_node_with_api_key() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(HTTPStatus.CREATED, json=_node_response_json())

    async with _store(handler) as store:
        await store.create_node(_node_request())

    (request,) = seen
    assert request.method == "POST"
    assert str(request.url) == f"{API_URL}/nodes"
    assert request.headers["x-api-key"] == "secret"


_SERVER_DERIVED_ANNOTATION = AnnotationResponse(
    label="x", connections=[ReferenceResponse(label="g", id="g", count=1)]
)
_SERVER_DERIVED_REFERENCE = ReferenceResponse(
    label="g", id="g", count=1, artifact_type=ArtifactType.FUNCTION
)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inputs", [_SERVER_DERIVED_ANNOTATION]),
        ("outputs", [_SERVER_DERIVED_ANNOTATION]),
        ("uses", [_SERVER_DERIVED_REFERENCE]),
        ("see_also", [_SERVER_DERIVED_REFERENCE]),
        (
            "wf_definition",
            WfDefinition(
                nodes=[
                    WfFunctionNode.model_construct(
                        node_id="n",
                        inputs=[_SERVER_DERIVED_ANNOTATION],
                        outputs=[],
                        atlas_id=None,
                    )
                ],
                edges=[],
            ),
        ),
    ],
)
async def test_create_node_rejects_server_owned_fields_before_sending(
    field: str, value: Any
) -> None:
    """Parsers build nodes with ``model_construct``, which skips validation, so
    a response-side value (with its server-derived fields) can end up inside a
    request. The store must refuse it instead of sending it to the backend.
    """
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(HTTPStatus.CREATED, json=_node_response_json())

    node = NodeRequest.model_construct(
        **{**dict(_node_request()), field: value},
    )

    async with _store(handler) as store:
        with pytest.raises(ValidationError):
            await store.create_node(node)

    assert seen == []


# --- read_node -----------------------------------------------------------


async def test_read_node_returns_node_on_ok() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(HTTPStatus.OK, json=_node_response_json())

    async with _store(handler) as store:
        node = await store.read_node("id-f")

    assert node is not None
    assert node.id == "id-f"
    assert str(seen[0].url) == f"{API_URL}/nodes/id-f"


async def test_read_node_returns_none_on_not_found() -> None:
    async with _store(_respond(HTTPStatus.NOT_FOUND)) as store:
        assert await store.read_node("missing") is None


@pytest.mark.parametrize("status_code", [HTTPStatus.BAD_REQUEST, 500, 503])
async def test_read_node_raises_on_other_errors(status_code: int) -> None:
    async with _store(_respond(status_code)) as store:
        with pytest.raises(NodeStoreError):
            await store.read_node("id-f")


async def test_read_node_does_not_require_api_key() -> None:
    async with _store(_respond(HTTPStatus.NOT_FOUND), api_key="") as store:
        assert await store.read_node("id-f") is None


# --- create_execution_result ---------------------------------------------


async def test_create_execution_result_returns_record_on_created() -> None:
    async with _store(
        _respond(HTTPStatus.CREATED, _execution_result_response_json())
    ) as store:
        result = await store.create_execution_result(_execution_result_request())

    assert result.id == "exec-1"


@pytest.mark.parametrize("status_code", [HTTPStatus.OK, HTTPStatus.CONFLICT, 500])
async def test_create_execution_result_raises_on_other_status(
    status_code: int,
) -> None:
    async with _store(
        _respond(status_code, _execution_result_response_json())
    ) as store:
        with pytest.raises(NodeStoreError):
            await store.create_execution_result(_execution_result_request())


# --- trigger_embed -------------------------------------------------------


@pytest.mark.parametrize("status_code", [HTTPStatus.OK, HTTPStatus.ACCEPTED])
async def test_trigger_embed_succeeds_on_success_status(status_code: int) -> None:
    async with _store(_respond(status_code)) as store:
        await store.trigger_embed()


async def test_trigger_embed_raises_not_configured_on_503() -> None:
    async with _store(_respond(HTTPStatus.SERVICE_UNAVAILABLE)) as store:
        with pytest.raises(EmbeddingNotConfiguredError):
            await store.trigger_embed()


@pytest.mark.parametrize("status_code", [HTTPStatus.BAD_REQUEST, 500])
async def test_trigger_embed_raises_on_other_errors(status_code: int) -> None:
    async with _store(_respond(status_code)) as store:
        with pytest.raises(NodeStoreError) as excinfo:
            await store.trigger_embed()
    assert not isinstance(excinfo.value, EmbeddingNotConfiguredError)


# --- authentication ------------------------------------------------------


async def _create_node(store: HttpNodeStore) -> object:
    return await store.create_node(_node_request())


async def _create_execution_result(store: HttpNodeStore) -> object:
    return await store.create_execution_result(_execution_result_request())


async def _trigger_embed(store: HttpNodeStore) -> object:
    return await store.trigger_embed()


@pytest.mark.parametrize(
    "call", [_create_node, _create_execution_result, _trigger_embed]
)
async def test_writes_require_api_key(
    call: Callable[[HttpNodeStore], Awaitable[object]],
) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(HTTPStatus.CREATED, json=_node_response_json())

    async with _store(handler, api_key="") as store:
        with pytest.raises(ValueError, match="API key"):
            await call(store)
    assert requests == []


# --- concurrency and lifecycle -------------------------------------------


async def test_concurrent_requests_overlap() -> None:
    """N concurrent calls are all in flight at once, i.e. no call blocks the
    event loop until its response arrives."""
    n = 5
    barrier = asyncio.Barrier(n)

    async def handler(request: httpx2.Request) -> httpx2.Response:
        await barrier.wait()
        name = request.url.path.rsplit("/", 1)[-1]
        return httpx2.Response(HTTPStatus.OK, json=_node_response_json(name))

    async with _store(handler) as store:
        nodes = await asyncio.wait_for(
            asyncio.gather(*(store.read_node(f"n{i}") for i in range(n))),
            timeout=5,
        )

    assert [node.name for node in nodes if node is not None] == [
        f"n{i}" for i in range(n)
    ]


class _RecordingTransport(httpx2.MockTransport):
    """``MockTransport`` that records whether the client closed it."""

    def __init__(self, handler: Handler) -> None:
        super().__init__(handler)
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("use_context_manager", [True, False])
async def test_closing_releases_connections(use_context_manager: bool) -> None:
    transport = _RecordingTransport(_respond(HTTPStatus.NOT_FOUND))
    store = HttpNodeStore(API_URL, "secret", transport=transport)

    if use_context_manager:
        async with store:
            await store.read_node("x")
    else:
        await store.read_node("x")
        await store.aclose()

    assert transport.closed


async def test_store_stays_usable_after_aclose() -> None:
    store = _store(_respond(HTTPStatus.NOT_FOUND))
    await store.read_node("x")
    await store.aclose()

    assert await store.read_node("x") is None
    await store.aclose()


async def test_aclose_without_use_is_harmless() -> None:
    store = _store(_respond(HTTPStatus.NOT_FOUND))
    await store.aclose()
    await store.aclose()


def test_store_is_usable_from_successive_event_loops() -> None:
    """Each ``asyncio.run`` is a new event loop; a store released at the end
    of one loop must work in the next one over real connections."""

    async def read_then_release(store: HttpNodeStore) -> None:
        try:
            assert await store.read_node("x") is None
        finally:
            await store.aclose()

    with http_backend() as api_url:
        store = HttpNodeStore(api_url, "secret")
        for _ in range(3):
            asyncio.run(read_then_release(store))
