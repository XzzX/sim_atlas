import uuid

import httpx

from sim_atlas_toolkit.models import ArtifactRequest, ExecutionResultRequest
from sim_atlas_toolkit.settings import EnrichmentSettings


def _mock_response() -> httpx.Response:
    return httpx.Response(201, json={"id": str(uuid.uuid4())})


class NodeStoreAPI:
    def __init__(self, enrichment_settings: EnrichmentSettings | None = None) -> None:
        self.uploaded: list[ArtifactRequest] = []
        self.uploaded_execution_results: list[ExecutionResultRequest] = []
        self.enrichment_settings = enrichment_settings

    async def upload(self, artifacts: list[ArtifactRequest]) -> list[httpx.Response]:
        self.uploaded.extend(artifacts)
        return [_mock_response() for _ in artifacts]

    async def upload_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> httpx.Response:
        self.uploaded_execution_results.append(execution_result)
        return _mock_response()
