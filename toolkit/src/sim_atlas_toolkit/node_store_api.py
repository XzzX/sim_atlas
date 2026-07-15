import logging

import httpx

from sim_atlas_toolkit.models import (
    ArtifactRequest,
    ExecutionResultRequest,
    artifact_request_adapter,
)

logger = logging.getLogger(__name__)


async def create_artifact(
    api_url: str,
    api_key: str | None,
    artifact: ArtifactRequest,
) -> httpx.Response:
    if not api_key:
        raise ValueError("API key is required to create an artifact")

    headers: dict[str, str] = {"x-api-key": api_key}

    return httpx.post(
        f"{api_url}/artifacts",
        json=artifact_request_adapter.dump_python(
            artifact_request_adapter.validate_python(artifact.model_dump())
        ),
        headers=headers,
    )


async def create_artifacts(
    api_url: str,
    api_key: str | None,
    artifacts: list[ArtifactRequest],
) -> list[httpx.Response]:
    return [await create_artifact(api_url, api_key, artifact) for artifact in artifacts]


async def create_execution_result(
    api_url: str,
    api_key: str | None,
    execution_result: ExecutionResultRequest,
) -> httpx.Response:
    if not api_key:
        raise ValueError("API key is required to create an execution result")

    headers: dict[str, str] = {"x-api-key": api_key}

    return httpx.post(
        f"{api_url}/execution_results",
        json=execution_result.model_dump(),
        headers=headers,
    )
