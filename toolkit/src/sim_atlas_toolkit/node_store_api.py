import logging

import httpx

from sim_atlas_toolkit.models import (
    ArtifactRequest,
    ExecutionResultRequest,
    artifact_request_adapter,
)

logger = logging.getLogger(__name__)


class NodeStoreAPI:
    def __init__(
        self, api_url: str, client: httpx.AsyncClient, api_key: str | None = None
    ) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self._client = client

    async def upload(self, artifacts: list[ArtifactRequest]) -> list[httpx.Response]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        responses: list[httpx.Response] = []
        for artifact in artifacts:
            request_data = artifact_request_adapter.validate_python(
                artifact.model_dump()
            )

            responses.append(
                await self._client.post(
                    f"{self.api_url}/artifacts",
                    json=artifact_request_adapter.dump_python(request_data),
                    headers=headers,
                )
            )
        return responses

    async def upload_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        return await self._client.post(
            f"{self.api_url}/execution_results",
            json=execution_result.model_dump(),
            headers=headers,
        )
