import uuid

import httpx
import pytest

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import ArtifactRequest, ExecutionResultRequest


def _mock_response() -> httpx.Response:
    return httpx.Response(201, json={"id": str(uuid.uuid4())})


class MockNodeStore:
    def __init__(self) -> None:
        self.uploaded: list[ArtifactRequest] = []
        self.uploaded_execution_results: list[ExecutionResultRequest] = []


def install_mock_node_store(monkeypatch: pytest.MonkeyPatch) -> MockNodeStore:
    """Replace the node_store_api HTTP calls with in-memory recording stubs."""
    store = MockNodeStore()

    async def create_artifact(
        api_url: str, api_key: str | None, artifact: ArtifactRequest
    ) -> httpx.Response:
        store.uploaded.append(artifact)
        return _mock_response()

    async def create_artifacts(
        api_url: str, api_key: str | None, artifacts: list[ArtifactRequest]
    ) -> list[httpx.Response]:
        store.uploaded.extend(artifacts)
        return [_mock_response() for _ in artifacts]

    async def create_execution_result(
        api_url: str, api_key: str | None, execution_result: ExecutionResultRequest
    ) -> httpx.Response:
        store.uploaded_execution_results.append(execution_result)
        return _mock_response()

    monkeypatch.setattr(node_store_api, "create_artifact", create_artifact)
    monkeypatch.setattr(node_store_api, "create_artifacts", create_artifacts)
    monkeypatch.setattr(
        node_store_api, "create_execution_result", create_execution_result
    )

    return store
