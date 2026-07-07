import uuid
from typing import Any

import requests

from sim_atlas_toolkit.models import ArtifactRequest, ExecutionResultRequest


class _MockResponse(requests.Response):
    def __init__(self, artifact_id: str) -> None:
        super().__init__()
        self.status_code = 201
        self._json_data = {"id": artifact_id}

    def json(self, **kwargs: Any) -> Any:
        return self._json_data


class NodeStoreAPI:
    def __init__(self) -> None:
        self.uploaded: list[ArtifactRequest] = []
        self.uploaded_execution_results: list[ExecutionResultRequest] = []

    def upload(self, artifacts: list[ArtifactRequest]) -> list[requests.Response]:
        self.uploaded.extend(artifacts)
        return [_MockResponse(str(uuid.uuid4())) for _ in artifacts]

    def upload_execution_result(
        self, execution_result: ExecutionResultRequest
    ) -> requests.Response:
        self.uploaded_execution_results.append(execution_result)
        return _MockResponse(str(uuid.uuid4()))
