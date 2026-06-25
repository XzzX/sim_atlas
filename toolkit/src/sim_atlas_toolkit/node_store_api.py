import logging

import requests

from sim_atlas_toolkit.models import (
    ArtifactRequest,
    artifact_request_adapter,
)

logger = logging.getLogger("SimAtlasAPI")


class NodeStoreAPI:
    def __init__(self, api_url: str, api_key: str | None = None) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def upload(self, artifacts: list[ArtifactRequest]) -> list[requests.Response]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        responses: list[requests.Response] = []
        for artifact in artifacts:
            request_data = artifact_request_adapter.validate_python(
                artifact.model_dump()
            )

            responses.append(
                requests.post(
                    f"{self.api_url}/artifacts",
                    json=artifact_request_adapter.dump_python(request_data),
                    headers=headers,
                )
            )
        return responses
