import uuid

import httpx2
import pytest

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import ExecutionResultRequest, NodeRequest


def _mock_response() -> httpx2.Response:
    return httpx2.Response(201, json={"id": str(uuid.uuid4())})


class MockNodeStore:
    def __init__(self) -> None:
        self.uploaded: list[NodeRequest] = []
        self.uploaded_execution_results: list[ExecutionResultRequest] = []
        self.embed_triggers: int = 0


def install_mock_node_store(monkeypatch: pytest.MonkeyPatch) -> MockNodeStore:
    """Replace the node_store_api HTTP calls with in-memory recording stubs."""
    store = MockNodeStore()

    async def create_node(
        api_url: str, api_key: str | None, node: NodeRequest
    ) -> httpx2.Response:
        store.uploaded.append(node)
        return _mock_response()

    async def create_nodes(
        api_url: str, api_key: str | None, nodes: list[NodeRequest]
    ) -> list[httpx2.Response]:
        store.uploaded.extend(nodes)
        return [_mock_response() for _ in nodes]

    async def read_node(api_url: str, node_id: str) -> httpx2.Response:
        return httpx2.Response(404)  # Not found

    async def create_execution_result(
        api_url: str, api_key: str | None, execution_result: ExecutionResultRequest
    ) -> httpx2.Response:
        store.uploaded_execution_results.append(execution_result)
        return _mock_response()

    async def trigger_embed(api_url: str, api_key: str | None) -> httpx2.Response:
        store.embed_triggers += 1
        return httpx2.Response(200)

    monkeypatch.setattr(node_store_api, "create_node", create_node)
    monkeypatch.setattr(node_store_api, "create_nodes", create_nodes)
    monkeypatch.setattr(node_store_api, "read_node", read_node)
    monkeypatch.setattr(
        node_store_api, "create_execution_result", create_execution_result
    )
    monkeypatch.setattr(node_store_api, "trigger_embed", trigger_embed)

    return store
