import logging

import httpx2

from sim_atlas_toolkit.models import (
    ExecutionResultRequest,
    NodeRequest,
    node_request_adapter,
)

logger = logging.getLogger(__name__)


async def create_node(
    api_url: str,
    api_key: str | None,
    node: NodeRequest,
) -> httpx2.Response:
    if not api_key:
        raise ValueError("API key is required to create a node")

    headers: dict[str, str] = {"x-api-key": api_key}

    return httpx2.post(
        f"{api_url}/nodes",
        json=node_request_adapter.dump_python(
            node_request_adapter.validate_python(node.model_dump())
        ),
        headers=headers,
    )


async def create_nodes(
    api_url: str,
    api_key: str | None,
    nodes: list[NodeRequest],
) -> list[httpx2.Response]:
    return [await create_node(api_url, api_key, node) for node in nodes]


async def read_node(
    api_url: str,
    node_id: str,
) -> httpx2.Response:
    return httpx2.get(
        f"{api_url}/nodes/{node_id}",
    )


async def trigger_embed(api_url: str, api_key: str | None) -> httpx2.Response:
    if not api_key:
        raise ValueError("API key is required to trigger embedding")

    headers: dict[str, str] = {"x-api-key": api_key}

    return httpx2.post(f"{api_url}/embed", headers=headers)


async def create_execution_result(
    api_url: str,
    api_key: str | None,
    execution_result: ExecutionResultRequest,
) -> httpx2.Response:
    if not api_key:
        raise ValueError("API key is required to create an execution result")

    headers: dict[str, str] = {"x-api-key": api_key}

    return httpx2.post(
        f"{api_url}/execution_results",
        json=execution_result.model_dump(),
        headers=headers,
    )
