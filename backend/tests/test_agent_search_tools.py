"""Characterisation tests for the Web IDE agent's catalog search tools.

These lock the exact text the agent's tools emit. The MCP surface renders the
same nodes in a Python-shaped format (see ``sim_atlas.mcp_server``); these
tests exist so that sharing helpers between the two surfaces cannot silently
change what the agent sees.
"""

from __future__ import annotations

import asyncio

import pytest

from sim_atlas.agent.tools._errors import ToolError
from sim_atlas.agent.tools._search import (
    GetNodeDetailsInput,
    SearchNodesInput,
    execute_get_node_details,
    execute_search_nodes,
)
from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.models import AnnotationResponse

from .test_storage_interface import make_node, make_workflow


@pytest.fixture
def storage() -> FileSystemStorage:
    return FileSystemStorage(path=None)


def test_execute_search_nodes_output_format(storage: FileSystemStorage) -> None:
    """The agent's search output is a fixed, position-sensitive text block."""
    node = make_node(
        id="node-1",
        name="test_node",
        brief_description="Adds two numbers.",
        inputs=[
            AnnotationResponse(
                label="a",
                datatype="float",
                unit="K",
                quantity="temperature",
                has_default_value=True,
                description="desc",
            )
        ],
        outputs=[AnnotationResponse(label="result", datatype="float")],
    )
    storage.create_node(node)

    result = asyncio.run(
        execute_search_nodes(SearchNodesInput(query="test_node"), storage, None)
    )

    assert result == (
        "Retrieved functions:\n"
        "\n"
        "[1] test_node\n"
        "atlas_node_id: node-1\n"
        "Summary:\n"
        "Adds two numbers.\n"
        "\n"
        "Inputs:\n"
        "a: float [K, temperature] (optional) — desc\n"
        "\n"
        "Outputs:\n"
        "result: float"
    )


def test_execute_search_nodes_falls_back_to_the_first_docstring_line(
    storage: FileSystemStorage,
) -> None:
    """Without a brief_description the summary is the docstring's first line."""
    storage.create_node(
        make_node(
            id="node-2",
            name="documented_node",
            brief_description="",
            docstring="First line.\nSecond line.",
        )
    )

    result = asyncio.run(
        execute_search_nodes(SearchNodesInput(query="documented_node"), storage, None)
    )

    assert "Summary:\nFirst line." in result
    assert "Second line." not in result


def test_execute_search_nodes_without_matches(storage: FileSystemStorage) -> None:
    result = asyncio.run(
        execute_search_nodes(SearchNodesInput(query="nothing"), storage, None)
    )

    assert result == "Retrieved functions:\n\n(no results found)"


def test_execute_get_node_details_output_format(storage: FileSystemStorage) -> None:
    storage.create_node(
        make_node(
            id="node-3",
            name="detailed_node",
            brief_description="A detailed node.",
            inputs=[AnnotationResponse(label="x", datatype="int")],
            outputs=[],
        )
    )

    result = asyncio.run(
        execute_get_node_details(
            GetNodeDetailsInput(atlas_node_id="node-3"), storage, None
        )
    )

    assert result == (
        "Node details:\n"
        "\n"
        "[1] detailed_node\n"
        "atlas_node_id: node-3\n"
        "Summary:\n"
        "A detailed node.\n"
        "\n"
        "Inputs:\n"
        "x: int"
    )


def test_execute_get_node_details_rejects_a_workflow_id(
    storage: FileSystemStorage,
) -> None:
    storage.create_node(make_workflow(id="wf-1"))

    with pytest.raises(ToolError):
        asyncio.run(
            execute_get_node_details(
                GetNodeDetailsInput(atlas_node_id="wf-1"), storage, None
            )
        )


def test_execute_get_node_details_with_unknown_id_raises(
    storage: FileSystemStorage,
) -> None:
    with pytest.raises(ToolError):
        asyncio.run(
            execute_get_node_details(
                GetNodeDetailsInput(atlas_node_id="missing"), storage, None
            )
        )
