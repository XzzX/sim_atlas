"""Produce the real NodeResponse fixture that the TypeScript apps parse (ADR-0027).

The frontend and web_ide tests parse ``api_schema/fixtures/workflow-node-response.json``
with the generated ``NodeResponseSchema``. That only proves something if the fixture is
what the API actually returns, so this test builds it through the HTTP API and fails
when the committed file is stale. Regenerate with::

    SIM_ATLAS_UPDATE_FIXTURES=1 uv run pytest tests/test_api_schema_fixture.py
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sim_atlas_models import (
    Annotation,
    ArtifactType,
    NodeRequest,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WfInputNode,
    WfOutputNode,
)

from sim_atlas.main import app
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage.file_system_storage import FileSystemStorage

FIXTURE = (
    Path(__file__).parents[2]
    / "api_schema"
    / "fixtures"
    / "workflow-node-response.json"
)
# The only value the server does not derive from the requests.
TIMESTAMP = "2026-01-01T00:00:00Z"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    storage = FileSystemStorage(path=None)
    monkeypatch.setattr("sim_atlas.main.get_storage_backend", lambda: storage)
    app.dependency_overrides[get_current_user] = lambda: Creator(
        name="Fixture Creator", email="creator@example.com"
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _port(label: str) -> Annotation:
    return Annotation(label=label, datatype="float")


def _function(name: str, inputs: list[str], output: str) -> NodeRequest:
    return NodeRequest(
        artifact_type=ArtifactType.FUNCTION,
        author_name="Fixture Author",
        author_email="author@example.com",
        name=f"dummy_module.flowrep.{name}",
        category="dummy_module>flowrep",
        keywords=["flowrep"],
        python_import=f"dummy_module.flowrep.{name}",
        source_code=f"def {name}({', '.join(inputs)}): ...",
        inputs=[_port(i) for i in inputs],
        outputs=[_port(output)],
    )


def _call(
    node_id: str, atlas_id: str, inputs: list[str], output: str
) -> WfFunctionNode:
    return WfFunctionNode(
        node_id=node_id,
        atlas_id=atlas_id,
        inputs=[_port(i) for i in inputs],
        outputs=[_port(output)],
    )


def _edge(src: str, src_port: str | None, dst: str, dst_port: str | None) -> WfEdge:
    return WfEdge(
        source_node=src, source_port=src_port, target_node=dst, target_port=dst_port
    )


def _workflow(
    name: str,
    inputs: list[str],
    output: str,
    uses: list[tuple[str, str]],
    calls: list[WfFunctionNode],
    edges: list[WfEdge],
) -> NodeRequest:
    return _function(name, inputs, output).model_copy(
        update={
            "artifact_type": ArtifactType.WORKFLOW,
            "uses": [Reference(label=label, id=id_, count=1) for label, id_ in uses],
            "wf_definition": WfDefinition(
                nodes=[
                    *(WfInputNode(node_id=i, outputs=[_port(i)]) for i in inputs),
                    *calls,
                    WfOutputNode(node_id=output, inputs=[_port(output)]),
                ],
                edges=edges,
            ),
        }
    )


def _create(client: TestClient, body: NodeRequest) -> str:
    response = client.post("/api/v1/nodes", json=body.model_dump(mode="json"))
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()["id"]


def build_fixture(client: TestClient) -> dict[str, Any]:
    """``linear`` (y = slope * x + intercept), used by the workflow ``twice``."""
    mul = _create(client, _function("mul", ["a", "b"], "product"))
    add = _create(client, _function("add", ["a", "b"], "sum"))
    linear = _create(
        client,
        _workflow(
            "linear",
            ["x", "slope", "intercept"],
            "result",
            uses=[("mul", mul), ("add", add)],
            calls=[
                _call("mul_0", mul, ["a", "b"], "product"),
                _call("add_0", add, ["a", "b"], "sum"),
            ],
            edges=[
                _edge("x", None, "mul_0", "a"),
                _edge("slope", None, "mul_0", "b"),
                _edge("mul_0", "product", "add_0", "a"),
                _edge("intercept", None, "add_0", "b"),
                _edge("add_0", "sum", "result", None),
            ],
        ),
    )
    _create(
        client,
        _workflow(
            "twice",
            ["x"],
            "y",
            uses=[("linear", linear), ("add", add)],
            calls=[
                _call("linear_0", linear, ["x", "slope", "intercept"], "result"),
                _call("add_0", add, ["a", "b"], "sum"),
            ],
            edges=[
                _edge("x", None, "linear_0", "x"),
                _edge("linear_0", "result", "add_0", "a"),
                _edge("linear_0", "result", "add_0", "b"),
                _edge("add_0", "sum", "y", None),
            ],
        ),
    )
    response = client.get(f"/api/v1/nodes/{linear}")
    assert response.status_code == status.HTTP_200_OK
    node = response.json()
    node["creation_timestamp"] = TIMESTAMP
    return node


def test_fixture_covers_the_derived_fields(client: TestClient) -> None:
    """The fixture exercises every server-derived part a client must parse."""
    node = build_fixture(client)
    assert node["artifact_type"] == "workflow"
    assert node["uses"]
    assert node["used_by"]
    assert any(port["connections"] for port in node["inputs"] + node["outputs"])
    assert node["wf_definition"]["nodes"]


def test_committed_fixture_matches_the_api(client: TestClient) -> None:
    node = build_fixture(client)
    expected = json.dumps(node, indent=2, sort_keys=True) + "\n"
    if os.environ.get("SIM_ATLAS_UPDATE_FIXTURES"):
        FIXTURE.parent.mkdir(exist_ok=True)
        FIXTURE.write_text(expected)
    assert FIXTURE.read_text() == expected, (
        "api_schema/fixtures/workflow-node-response.json is stale; regenerate it "
        "with SIM_ATLAS_UPDATE_FIXTURES=1 uv run pytest "
        "tests/test_api_schema_fixture.py"
    )
