from http import HTTPStatus

import httpx2

from sim_atlas_toolkit.models import (
    ExecutionResultRequest,
    ExecutionResultResponse,
    NodeRequest,
    NodeResponse,
    node_request_adapter,
    node_response_adapter,
)
from sim_atlas_toolkit.node_store import (
    EmbeddingNotConfiguredError,
    NodeResult,
    NodeStatus,
    NodeStore,
    NodeStoreError,
)


class HttpNodeStore(NodeStore):
    """``NodeStore`` backed by a Sim Atlas backend over HTTP."""

    def __init__(self, api_url: str, api_key: str) -> None:
        self._api_url = api_url
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ValueError("API key is required to write to the node store")
        return {"x-api-key": self._api_key}

    async def create_node(self, node: NodeRequest) -> NodeResult:
        response = httpx2.post(
            f"{self._api_url}/nodes",
            json=node_request_adapter.dump_python(
                node_request_adapter.validate_python(node.model_dump())
            ),
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
            node=node_response_adapter.validate_python(response.json()),
        )

    async def read_node(self, node_id: str) -> NodeResponse | None:
        response = httpx2.get(f"{self._api_url}/nodes/{node_id}")
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        if response.status_code != HTTPStatus.OK:
            raise NodeStoreError(
                f"GET {self._api_url}/nodes/{node_id} failed with status "
                f"{response.status_code}"
            )
        return node_response_adapter.validate_python(response.json())

    async def create_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> ExecutionResultResponse:
        response = httpx2.post(
            f"{self._api_url}/execution_results",
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
        response = httpx2.post(f"{self._api_url}/embed", headers=self._headers)
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            raise EmbeddingNotConfiguredError(
                "backend has no embedding provider configured"
            )
        if response.is_error:
            raise NodeStoreError(
                f"POST {self._api_url}/embed failed with status {response.status_code}"
            )
