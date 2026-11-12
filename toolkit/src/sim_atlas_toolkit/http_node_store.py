from http import HTTPStatus

import httpx2
from sim_atlas_models import (
    ExecutionResultRequest,
    ExecutionResultResponse,
    NodeRequest,
    NodeResponse,
)

from sim_atlas_toolkit.node_store import (
    EmbeddingNotConfiguredError,
    NodeResult,
    NodeStatus,
    NodeStore,
    NodeStoreError,
)


def _validated(node: NodeRequest) -> NodeRequest:
    """Re-validate *node*, which parsers build unvalidated (``model_construct``).

    ``serialize_as_any`` dumps nested values as what they are rather than as
    their declared type, so a response-side value smuggled into the request
    (e.g. an ``AnnotationResponse`` with ``connections``) keeps its
    server-owned fields and fails ``extra="forbid"`` instead of being
    silently stripped.
    """
    return NodeRequest.model_validate(node.model_dump(serialize_as_any=True))


class HttpNodeStore(NodeStore):
    """``NodeStore`` backed by a Sim Atlas backend over HTTP.

    Requests share one ``httpx2.AsyncClient``, created on first use. Its
    pooled connections belong to the event loop that opened them, so release
    them (``aclose`` or ``async with``) before that loop ends; the store then
    opens a fresh client on its next request. *transport* overrides the
    client's network transport, e.g. ``httpx2.MockTransport`` in tests.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._transport = transport
        self._client: httpx2.AsyncClient | None = None

    @property
    def _http(self) -> httpx2.AsyncClient:
        if self._client is None:
            self._client = httpx2.AsyncClient(
                base_url=self._api_url, transport=self._transport
            )
        return self._client

    async def aclose(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    @property
    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError("API key is required to write to the node store")
        return {"x-api-key": self._api_key}

    async def create_node(self, node: NodeRequest) -> NodeResult:
        response = await self._http.post(
            "/nodes",
            json=_validated(node).model_dump(mode="json"),
            headers=self._headers,
        )
        if response.status_code == HTTPStatus.CREATED:
            status = NodeStatus.CREATED
        elif response.status_code == HTTPStatus.CONFLICT:
            status = NodeStatus.EXISTS
        else:
            raise NodeStoreError(
                f"POST {self._api_url}/nodes failed with status {response.status_code}"
            )
        return NodeResult(
            status=status,
            node=NodeResponse.model_validate(response.json()),
        )

    async def read_node(self, node_id: str) -> NodeResponse | None:
        response = await self._http.get(f"/nodes/{node_id}")
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        if response.status_code != HTTPStatus.OK:
            raise NodeStoreError(
                f"GET {self._api_url}/nodes/{node_id} failed with status "
                f"{response.status_code}"
            )
        return NodeResponse.model_validate(response.json())

    async def create_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> ExecutionResultResponse:
        response = await self._http.post(
            "/execution_results",
            json=execution_result.model_dump(),
            headers=self._headers,
        )
        if response.status_code != HTTPStatus.CREATED:
            raise NodeStoreError(
                f"POST {self._api_url}/execution_results failed with status "
                f"{response.status_code}"
            )
        return ExecutionResultResponse.model_validate(response.json())

    async def trigger_embed(self) -> None:
        response = await self._http.post("/embed", headers=self._headers)
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            raise EmbeddingNotConfiguredError(
                "backend has no embedding provider configured"
            )
        if response.is_error:
            raise NodeStoreError(
                f"POST {self._api_url}/embed failed with status {response.status_code}"
            )
