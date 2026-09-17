"""HTTP-level tests for the main FastAPI app."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Generator
from math import ceil
from types import SimpleNamespace
from typing import Any, Protocol, cast

import httpx2
import numpy as np
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from fastmcp import Client
from fastmcp.exceptions import ToolError

from sim_atlas.api.artifacts import compose_artifact
from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.main import app, mcp
from sim_atlas.models import (
    AnnotationRequest,
    ArtifactType,
    FunctionRequest,
    ScoredSearchResponse,
    SearchResults,
    WfDefinition,
    WfEdge,
    WfInputNode,
    WfOutputNode,
    WorkflowRequest,
)
from sim_atlas.security import Creator, get_current_user
from sim_atlas.static_files import is_asset_path

from .test_storage_interface import make_node

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

TEST_CREATOR = Creator(name="Test User", email="test@example.com")


class ApiClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> httpx2.Response: ...
    def post(self, url: str, **kwargs: Any) -> httpx2.Response: ...
    def put(self, url: str, **kwargs: Any) -> httpx2.Response: ...
    def delete(self, url: str, **kwargs: Any) -> httpx2.Response: ...


# ---------------------------------------------------------------------------
# Request body factories
# ---------------------------------------------------------------------------


def make_function_request_body(**kwargs: Any) -> dict[str, Any]:
    """Return a JSON-serialisable dict for a FunctionRequest with sensible defaults."""
    defaults: dict[str, Any] = {
        "artifact_type": "function",
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "name": "add_numbers",
        "category": "math",
        "keywords": ["add", "math"],
        "python_import": "mylib.add_numbers",
        "source_code": "def add_numbers(a, b):\n    return a + b\n",
        "docstring": "Adds two numbers.",
        "inputs": [{"label": "a"}, {"label": "b"}],
        "outputs": [{"label": "result"}],
    }
    defaults.update(kwargs)
    return defaults


def make_workflow_request_body(**kwargs: Any) -> dict[str, Any]:
    """Return a JSON-serialisable dict for a WorkflowRequest with sensible defaults."""
    defaults: dict[str, Any] = {
        "artifact_type": "workflow",
        "author_name": "Bob",
        "author_email": "bob@example.com",
        "name": "my_workflow",
        "category": "analysis",
        "keywords": ["workflow"],
        "source_code": "",
        "docstring": "A test workflow.",
        "inputs": [{"label": "x"}],
        "outputs": [{"label": "y"}],
        "definition": {
            "nodes": [
                {"id": "i1", "type": "input", "name": "x"},
                {"id": "o1", "type": "output", "name": "y"},
            ],
            "edges": [{"source": "i1", "target": "o1"}],
        },
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage() -> FileSystemStorage:
    return FileSystemStorage(path=None)


@pytest.fixture
def client(
    storage: FileSystemStorage, monkeypatch: pytest.MonkeyPatch
) -> Generator[ApiClient]:
    monkeypatch.setattr("sim_atlas.main.get_storage_backend", lambda: storage)
    app.dependency_overrides[get_current_user] = lambda: TEST_CREATOR
    with TestClient(app) as c:
        yield cast(ApiClient, c)
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(
    storage: FileSystemStorage, monkeypatch: pytest.MonkeyPatch
) -> Generator[ApiClient]:
    monkeypatch.setattr("sim_atlas.main.get_storage_backend", lambda: storage)
    with TestClient(app) as c:
        yield cast(ApiClient, c)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth endpoint
# ---------------------------------------------------------------------------


def test_me_returns_creator(client: ApiClient) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == TEST_CREATOR.name
    assert body["email"] == TEST_CREATOR.email


def test_me_unauthenticated_returns_401(unauthed_client: ApiClient) -> None:
    response = unauthed_client.get("/api/v1/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Agent endpoint
# ---------------------------------------------------------------------------


class _NoLLMSettings:
    """Settings stand-in for a server without any LLM configuration."""

    llm_api_key = None
    llm_base_url = None
    llm_chat_model = None


def test_agent_stream_without_any_credentials_returns_503(
    client: ApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The route is always registered, so an unconfigured server must say 503."""
    monkeypatch.setattr("sim_atlas.agent._runner.load_settings", _NoLLMSettings)

    response = client.post(
        "/api/v1/agent/stream",
        json={"query": "build me a workflow", "nodes": [], "edges": []},
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_agent_stream_with_a_key_but_no_server_provider_returns_503(
    client: ApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller's key cannot substitute for the server-side base URL and model."""
    monkeypatch.setattr("sim_atlas.agent._runner.load_settings", _NoLLMSettings)

    response = client.post(
        "/api/v1/agent/stream",
        json={
            "query": "hi",
            "nodes": [],
            "edges": [],
            "llm_api_key": "user-key",
        },
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Artifact CRUD — create
# ---------------------------------------------------------------------------


def test_create_function_artifact_returns_201(client: ApiClient) -> None:
    response = client.post("/api/v1/artifacts", json=make_function_request_body())
    assert response.status_code == status.HTTP_201_CREATED
    artifact_id = response.json()["id"]
    assert isinstance(artifact_id, str)
    assert len(artifact_id) > 0


def test_create_workflow_artifact_returns_201(client: ApiClient) -> None:
    response = client.post("/api/v1/artifacts", json=make_workflow_request_body())
    assert response.status_code == status.HTTP_201_CREATED
    artifact_id = response.json()["id"]
    assert isinstance(artifact_id, str)


def test_create_duplicate_artifact_returns_409(client: ApiClient) -> None:
    body = make_function_request_body()
    client.post("/api/v1/artifacts", json=body)
    response = client.post("/api/v1/artifacts", json=body)
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_artifact_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.post(
        "/api/v1/artifacts", json=make_function_request_body()
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Artifact CRUD — read
# ---------------------------------------------------------------------------


def test_read_artifact_returns_200(client: ApiClient) -> None:
    artifact_id = client.post(
        "/api/v1/artifacts", json=make_function_request_body()
    ).json()["id"]
    response = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "add_numbers"
    assert body["artifact_type"] == ArtifactType.FUNCTION


def test_read_artifact_not_found_returns_404(client: ApiClient) -> None:
    response = client.get("/api/v1/artifacts/does-not-exist")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Artifact CRUD — update
# ---------------------------------------------------------------------------


def test_update_artifact_returns_updated_data(client: ApiClient) -> None:
    artifact_id = client.post(
        "/api/v1/artifacts", json=make_function_request_body()
    ).json()["id"]
    updated_body = make_function_request_body(
        name="updated_function",
        source_code="def updated_function(): pass",
    )
    response = client.put(f"/api/v1/artifacts/{artifact_id}", json=updated_body)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "updated_function"


def test_update_artifact_not_found_returns_404(client: ApiClient) -> None:
    response = client.put(
        "/api/v1/artifacts/does-not-exist", json=make_function_request_body()
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_artifact_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.put(
        "/api/v1/artifacts/some-id", json=make_function_request_body()
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Artifact CRUD — delete
# ---------------------------------------------------------------------------


def test_delete_artifact_returns_200_and_removes_artifact(client: ApiClient) -> None:
    artifact_id = client.post(
        "/api/v1/artifacts", json=make_function_request_body()
    ).json()["id"]
    response = client.delete(f"/api/v1/artifacts/{artifact_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "deleted" in response.json()["detail"].lower()
    assert (
        client.get(f"/api/v1/artifacts/{artifact_id}").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_delete_artifact_not_found_returns_404(client: ApiClient) -> None:
    response = client.delete("/api/v1/artifacts/does-not-exist")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_artifact_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.delete("/api/v1/artifacts/some-id")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Filter options
# ---------------------------------------------------------------------------


def test_filter_options_empty_storage(client: ApiClient) -> None:
    response = client.get("/api/v1/filter_options")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["author"] == []
    assert body["keywords"] == []


def test_filter_options_populated_after_creating_artifact(client: ApiClient) -> None:
    client.post(
        "/api/v1/artifacts",
        json=make_function_request_body(
            keywords=["unique-kw"], author_name="UniqueAuthor"
        ),
    )
    response = client.get("/api/v1/filter_options")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "UniqueAuthor" in body["author"]
    assert "unique-kw" in body["keywords"]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_with_no_query_returns_200(client: ApiClient) -> None:
    response = client.post("/api/v1/search", json={})
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()


def test_search_with_query_finds_matching_artifact(client: ApiClient) -> None:
    client.post("/api/v1/artifacts", json=make_function_request_body(name="special_fn"))
    response = client.post("/api/v1/search", json={"query": "special_fn"})
    assert response.status_code == status.HTTP_200_OK
    names = [item["node"]["name"] for item in response.json()["results"]["data"]]
    assert "special_fn" in names


def test_search_with_filter_returns_filtered_results(client: ApiClient) -> None:
    client.post(
        "/api/v1/artifacts",
        json=make_function_request_body(category="unique-cat"),
    )
    response = client.post(
        "/api/v1/search", json={"filter": {"category": "unique-cat"}}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"]["total_items"] >= 1


def test_search_pagination_fields_are_correct(client: ApiClient) -> None:
    page_size = 2
    total_artifacts = 3
    for i in range(total_artifacts):
        client.post(
            "/api/v1/artifacts",
            json=make_function_request_body(
                name=f"fn_{i}",
                source_code=f"def fn_{i}(): pass",
            ),
        )
    response = client.post("/api/v1/search", json={"page": 1, "limit": page_size})
    assert response.status_code == status.HTTP_200_OK
    results = response.json()["results"]
    assert results["page"] == 1
    assert results["limit"] == page_size
    assert results["total_items"] == total_artifacts
    assert results["total_pages"] == ceil(total_artifacts / page_size)
    assert len(results["data"]) == page_size


def test_search_limit_above_cap_returns_422(client: ApiClient) -> None:
    response = client.post("/api/v1/search", json={"limit": 9999})
    assert response.status_code == 422  # noqa: PLR2004


def test_search_does_not_leak_embedding(
    client: ApiClient, storage: FileSystemStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Search items hold the stored artifacts; the response model must strip embeddings."""
    dim = 16
    storage.create_artifact(
        make_node(
            name="embedded_fn",
            source_code="def embedded_fn(): pass",
            embedding=np.arange(dim, dtype=np.float32),
        )
    )

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.ones((len(documents), dim), dtype=np.float32)

    monkeypatch.setattr(
        "sim_atlas.file_system_storage.load_settings",
        lambda: SimpleNamespace(embeddings_enabled=True),
    )
    monkeypatch.setattr("sim_atlas.file_system_storage.create_embedding", _fake_embed)

    response = client.post("/api/v1/search", json={"query": "embedded_fn"})

    assert response.status_code == 200  # noqa: PLR2004
    assert response.json()["results"]["total_items"] == 1
    assert "embedding" not in response.text


def test_search_matches_a_partial_word(client: ApiClient) -> None:
    """The keyword-only path must already match mid-word, not just whole tokens."""
    client.post(
        "/api/v1/artifacts", json=make_function_request_body(name="get_temperature")
    )
    response = client.post("/api/v1/search", json={"query": "temp"})
    assert response.status_code == status.HTTP_200_OK
    names = [item["node"]["name"] for item in response.json()["results"]["data"]]
    assert "get_temperature" in names


# ---------------------------------------------------------------------------
# Suggest: the fast type-ahead lookup
# ---------------------------------------------------------------------------


def test_suggest_returns_matching_names_with_ids(client: ApiClient) -> None:
    response = client.post(
        "/api/v1/artifacts", json=make_function_request_body(name="special_fn")
    )
    artifact_id = response.json()["id"]

    response = client.post("/api/v1/suggest", json={"query": "spec"})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == artifact_id
    assert body[0]["name"] == "special_fn"


def test_suggest_matches_a_partial_word(client: ApiClient) -> None:
    """The reported regression, end to end: 'temp' must find 'get_temperature'."""
    client.post(
        "/api/v1/artifacts", json=make_function_request_body(name="get_temperature")
    )
    response = client.post("/api/v1/suggest", json={"query": "temp"})
    assert response.status_code == status.HTTP_200_OK
    names = [item["name"] for item in response.json()]
    assert "get_temperature" in names


def test_suggest_honours_filter(client: ApiClient) -> None:
    client.post(
        "/api/v1/artifacts",
        json=make_function_request_body(name="calc_physics", category="physics"),
    )
    client.post(
        "/api/v1/artifacts",
        json=make_function_request_body(
            name="calc_chemistry",
            category="chemistry",
            source_code="def calc_chemistry(): pass",
        ),
    )
    response = client.post(
        "/api/v1/suggest",
        json={"query": "calc", "filter": {"category": "physics"}},
    )
    assert response.status_code == status.HTTP_200_OK
    names = [item["name"] for item in response.json()]
    assert names == ["calc_physics"]


def test_suggest_honours_limit(client: ApiClient) -> None:
    for i in range(3):
        client.post(
            "/api/v1/artifacts",
            json=make_function_request_body(
                name=f"calc_{i}", source_code=f"def calc_{i}(): pass"
            ),
        )
    response = client.post("/api/v1/suggest", json={"query": "calc", "limit": 2})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2  # noqa: PLR2004


def test_suggest_limit_above_cap_returns_422(client: ApiClient) -> None:
    response = client.post("/api/v1/suggest", json={"query": "a", "limit": 9999})
    assert response.status_code == 422  # noqa: PLR2004


def test_suggest_missing_query_returns_422(client: ApiClient) -> None:
    response = client.post("/api/v1/suggest", json={})
    assert response.status_code == 422  # noqa: PLR2004


def test_suggest_empty_query_returns_empty(client: ApiClient) -> None:
    client.post("/api/v1/artifacts", json=make_function_request_body(name="special_fn"))
    response = client.post("/api/v1/suggest", json={"query": "   "})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_suggest_is_public(unauthed_client: ApiClient) -> None:
    response = unauthed_client.post("/api/v1/suggest", json={"query": "anything"})
    assert response.status_code == status.HTTP_200_OK


def test_suggest_returns_only_the_suggestion_fields(client: ApiClient) -> None:
    """The response model must strip everything but the type-ahead fields."""
    client.post("/api/v1/artifacts", json=make_function_request_body(name="special_fn"))
    response = client.post("/api/v1/suggest", json={"query": "special"})
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert set(body[0]) == {
        "id",
        "name",
        "python_import",
        "artifact_type",
        "short_description",
    }


# ---------------------------------------------------------------------------
# Hybrid vs. forced-keyword routing (storage.search_hybrid monkeypatched)
# ---------------------------------------------------------------------------


def _empty_search_response() -> ScoredSearchResponse:
    return ScoredSearchResponse(
        results=SearchResults(data=[], page=1, limit=10, total_items=0, total_pages=0)
    )


def test_search_with_query_uses_hybrid(
    client: ApiClient,
    storage: FileSystemStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def mock_search_hybrid(*args: Any, **kwargs: Any) -> ScoredSearchResponse:
        nonlocal called
        called = True
        return _empty_search_response()

    monkeypatch.setattr(storage, "search_hybrid", mock_search_hybrid)
    response = client.post("/api/v1/search", json={"query": "test"})
    assert response.status_code == status.HTTP_200_OK
    assert called


def test_search_semantic_false_forces_keyword(
    client: ApiClient,
    storage: FileSystemStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*args: Any, **kwargs: Any) -> ScoredSearchResponse:
        raise AssertionError("search_hybrid must not run when semantic=false")

    monkeypatch.setattr(storage, "search_hybrid", boom)
    response = client.post("/api/v1/search", json={"query": "test", "semantic": False})
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()


# ---------------------------------------------------------------------------
# MCP tool surface (ADR-0019)
# ---------------------------------------------------------------------------

MCP_TOOL_NAMES = [
    "find_by_signature",
    "get_function",
    "get_workflow_source",
    "search_functions",
]


def _call_mcp(name: str, args: dict[str, Any]) -> str:
    async def run() -> str:
        async with Client(mcp) as c:
            return cast(str, (await c.call_tool(name, args)).data)

    return asyncio.run(run())


def _seed_function(client: ApiClient, **kwargs: Any) -> str:
    response = client.post(
        "/api/v1/artifacts", json=make_function_request_body(**kwargs)
    )
    return cast(str, response.json()["id"])


def _seed_workflow(client: ApiClient, **kwargs: Any) -> str:
    response = client.post(
        "/api/v1/artifacts", json=make_workflow_request_body(**kwargs)
    )
    return cast(str, response.json()["id"])


def test_mcp_lists_the_python_tool_surface(client: ApiClient) -> None:
    """The surface is exactly four read-only tools; no write tool may appear."""

    async def run() -> list[tuple[str, str | None, Any]]:
        async with Client(mcp) as c:
            return [
                (t.name, t.description, t.annotations) for t in await c.list_tools()
            ]

    tools = asyncio.run(run())

    assert sorted(name for name, _, _ in tools) == MCP_TOOL_NAMES
    for _, description, hints in tools:
        assert description
        assert hints is not None
        assert hints.read_only_hint is True


def test_mcp_search_functions_returns_a_signature_and_import(client: ApiClient) -> None:
    _seed_function(
        client,
        python_import="mylib.math.add_numbers",
        inputs=[
            {"label": "a", "datatype": "float", "unit": "m", "quantity": "length"},
            {"label": "b", "datatype": "float"},
        ],
        outputs=[{"label": "result", "datatype": "float"}],
    )

    text = _call_mcp("search_functions", {"query": "add_numbers"})

    assert "def add_numbers(a: float, b: float) -> float" in text
    assert "from mylib.math import add_numbers" in text
    assert "# id:" in text
    assert "unit: m" in text
    assert "quantity: length" in text


def test_mcp_search_functions_caps_results_at_five(client: ApiClient) -> None:
    for i in range(8):
        _seed_function(
            client, name=f"mcp_fn_{i}", source_code=f"def mcp_fn_{i}(): pass"
        )

    text = _call_mcp("search_functions", {"query": "mcp_fn"})

    assert text.count("# id:") == 5  # noqa: PLR2004


def test_mcp_search_functions_omits_source_code(client: ApiClient) -> None:
    """Search output must stay small: import the function, do not copy it."""
    _seed_function(
        client, source_code="def add_numbers():\n    return 'SOURCE_MARKER'\n"
    )

    text = _call_mcp("search_functions", {"query": "add_numbers"})

    assert "SOURCE_MARKER" not in text


def test_mcp_search_functions_kind_workflow_returns_only_workflows(
    client: ApiClient,
) -> None:
    _seed_function(client, name="shared_topic_function")
    _seed_workflow(client, name="shared_topic_workflow", source_code="def wf(): pass")

    text = _call_mcp("search_functions", {"query": "shared_topic", "kind": "workflow"})

    assert "shared_topic_workflow" in text or "(workflow)" in text
    assert "shared_topic_function" not in text


def test_mcp_search_functions_without_matches_suggests_giving_up(
    client: ApiClient,
) -> None:
    text = _call_mcp("search_functions", {"query": "zzz_no_such_thing"})

    assert "No matches" in text
    assert "find_by_signature" in text
    assert "write the code yourself" in text


def test_mcp_search_functions_matches_a_sentence_shaped_query(
    client: ApiClient,
) -> None:
    """The query schema demands full sentences, so a full sentence must work.

    With no embedding provider configured this runs the keyword-only path,
    which is exactly how a zero-config deployment serves a coding agent.
    """
    _seed_function(
        client,
        name="gradient_on_mesh",
        python_import="mylib.mesh.gradient_on_mesh",
        source_code="def gradient_on_mesh(field): pass",
        docstring="Gradient of a scalar field on an unstructured mesh.",
    )
    _seed_function(
        client,
        name="add_numbers",
        python_import="mylib.add_numbers",
        source_code="def add_numbers(a, b): pass",
        docstring="Adds two numbers.",
    )

    text = _call_mcp(
        "search_functions",
        {
            "query": "compute the gradient of a temperature field on an unstructured mesh"
        },
    )

    assert "from mylib.mesh import gradient_on_mesh" in text
    assert "No matches" not in text


def test_mcp_find_by_signature_filters_on_a_parameter_unit(client: ApiClient) -> None:
    _seed_function(
        client,
        name="takes_kelvin",
        source_code="def takes_kelvin(t): pass",
        python_import="mylib.takes_kelvin",
        inputs=[{"label": "t", "datatype": "float", "unit": "K"}],
    )
    _seed_function(
        client,
        name="takes_metres",
        source_code="def takes_metres(d): pass",
        python_import="mylib.takes_metres",
        inputs=[{"label": "d", "datatype": "float", "unit": "m"}],
    )

    text = _call_mcp("find_by_signature", {"unit": "K", "match": "parameter"})

    assert "takes_kelvin" in text
    assert "takes_metres" not in text


def test_mcp_find_by_signature_match_return_uses_output_ports(
    client: ApiClient,
) -> None:
    _seed_function(
        client,
        name="produces_temperature",
        source_code="def produces_temperature(): pass",
        python_import="mylib.produces_temperature",
        inputs=[{"label": "x"}],
        outputs=[{"label": "t", "datatype": "float", "quantity": "temperature"}],
    )

    found = _call_mcp(
        "find_by_signature", {"quantity": "temperature", "match": "return"}
    )
    not_found = _call_mcp(
        "find_by_signature", {"quantity": "temperature", "match": "parameter"}
    )

    assert "produces_temperature" in found
    assert "No matches" in not_found


def test_mcp_find_by_signature_without_criteria_raises(client: ApiClient) -> None:
    with pytest.raises(ToolError) as exc:
        _call_mcp("find_by_signature", {"query": "anything"})

    assert "search_functions" in str(exc.value)


def test_mcp_find_by_signature_query_ranks_but_never_excludes(
    client: ApiClient,
) -> None:
    """The annotation filters constrain; the optional query only orders them.

    Passing a helpful description used to drop every result, so the tool
    punished an agent for filling in the optional field.
    """
    _seed_function(
        client,
        name="takes_kelvin",
        source_code="def takes_kelvin(t): pass",
        python_import="mylib.takes_kelvin",
        docstring="Accepts a temperature.",
        inputs=[{"label": "t", "datatype": "float", "unit": "K"}],
    )
    _seed_function(
        client,
        name="also_takes_kelvin",
        source_code="def also_takes_kelvin(t): pass",
        python_import="mylib.also_takes_kelvin",
        docstring="Something else entirely.",
        inputs=[{"label": "t", "datatype": "float", "unit": "K"}],
    )

    unqueried = _call_mcp("find_by_signature", {"unit": "K"})
    queried = _call_mcp(
        "find_by_signature",
        {"unit": "K", "query": "accepts a temperature in kelvin"},
    )

    # "takes_kelvin" is a substring of "also_takes_kelvin", so anchor on the
    # rendered signature line to tell the two entries apart.
    for text in (unqueried, queried):
        assert "def takes_kelvin(" in text
        assert "def also_takes_kelvin(" in text
    # The query decides the order without removing the weaker match.
    assert queried.index("def takes_kelvin(") < queried.index("def also_takes_kelvin(")


def test_mcp_get_function_returns_full_docstring_and_parameters(
    client: ApiClient,
) -> None:
    artifact_id = _seed_function(
        client,
        docstring="Adds two numbers.\n\nWith a longer explanation.",
        inputs=[{"label": "a", "datatype": "float"}],
    )

    text = _call_mcp("get_function", {"id": artifact_id})

    assert "With a longer explanation." in text
    assert "Parameters:" in text
    assert "from mylib import add_numbers" in text


def test_mcp_get_function_with_unknown_id_raises(client: ApiClient) -> None:
    with pytest.raises(ToolError) as exc:
        _call_mcp("get_function", {"id": "no-such-id"})

    assert "no-such-id" in str(exc.value)


def test_mcp_get_workflow_source_returns_stored_python(client: ApiClient) -> None:
    artifact_id = _seed_workflow(
        client,
        python_import="mylib.flows.linear",
        source_code="def linear(x):\n    return 2 * x\n",
    )

    text = _call_mcp("get_workflow_source", {"id": artifact_id})

    assert "return 2 * x" in text
    assert "from mylib.flows import linear" in text


def test_mcp_get_workflow_source_labels_a_json_workflow_definition(
    client: ApiClient,
) -> None:
    artifact_id = _seed_workflow(client, source_code='{"nodes": [], "edges": []}')

    text = _call_mcp("get_workflow_source", {"id": artifact_id})

    assert "not executable Python" in text


def test_mcp_get_workflow_source_rejects_a_function_id(client: ApiClient) -> None:
    artifact_id = _seed_function(client)

    with pytest.raises(ToolError) as exc:
        _call_mcp("get_workflow_source", {"id": artifact_id})

    assert "get_function" in str(exc.value)


def test_mcp_tools_never_leak_embeddings(
    client: ApiClient, storage: FileSystemStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The renderers read declared fields only; embeddings must never appear."""
    dim = 16
    node = make_node(
        name="embedded_fn",
        source_code="def embedded_fn(): pass",
        embedding=np.arange(dim, dtype=np.float32),
    )
    storage.create_artifact(node)

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.ones((len(documents), dim), dtype=np.float32)

    monkeypatch.setattr(
        "sim_atlas.file_system_storage.load_settings",
        lambda: SimpleNamespace(embeddings_enabled=True),
    )
    monkeypatch.setattr("sim_atlas.file_system_storage.create_embedding", _fake_embed)

    search_text = _call_mcp("search_functions", {"query": "embedded_fn"})
    detail_text = _call_mcp("get_function", {"id": node.id})

    assert "embedding" not in search_text
    assert "embedding" not in detail_text


def test_mcp_install_hint_uses_recorded_packages(client: ApiClient) -> None:
    _seed_function(
        client,
        packages=[
            {
                "ecosystem": "conda",
                "name": "mylib",
                "version": "1.4.0",
                "channel": "conda-forge",
            },
            {"ecosystem": "pypi", "name": "mylib", "version": "1.4.0"},
        ],
    )

    text = _call_mcp("search_functions", {"query": "add_numbers"})

    assert "# install: conda install -c conda-forge mylib=1.4.0" in text
    assert '# install: pip install "mylib==1.4.0"' in text


# ---------------------------------------------------------------------------
# compose_artifact unit tests
# ---------------------------------------------------------------------------


def test_compose_artifact_function_sets_expected_fields() -> None:
    request = FunctionRequest(
        author_name="Alice",
        author_email="alice@example.com",
        name="my_fn",
        category="science",
        keywords=["test"],
        python_import="mylib.my_fn",
        source_code="def my_fn(): pass",
        docstring="Does something.",
        inputs=[],
        outputs=[],
    )
    creator = Creator(name="Dev", email="dev@example.com")

    artifact = compose_artifact(request, creator)

    assert artifact.creator_name == "Dev"
    assert artifact.creator_email == "dev@example.com"
    assert len(artifact.id) > 0
    assert artifact.creation_timestamp != ""
    expected_hash = hashlib.sha256(request.source_code.encode()).hexdigest()
    assert artifact.hash == expected_hash


def test_compose_artifact_workflow_sets_expected_fields() -> None:
    wf_definition = WfDefinition(
        nodes=[
            WfInputNode(node_id="i1", outputs=[AnnotationRequest(label="i1")]),
            WfOutputNode(node_id="o1", inputs=[AnnotationRequest(label="o1")]),
        ],
        edges=[WfEdge(source_node="i1", target_node="o1")],
    )
    request = WorkflowRequest(
        name="my_wf",
        category="pipeline",
        keywords=["wf"],
        source_code=wf_definition.model_dump_json(),
        docstring="A workflow.",
        inputs=[AnnotationRequest(label="i1")],
        outputs=[AnnotationRequest(label="o1")],
        wf_definition=wf_definition,
    )
    creator = Creator(name="Dev", email="dev@example.com")

    artifact = compose_artifact(request, creator)

    assert artifact.creator_name == "Dev"
    assert len(artifact.id) > 0
    expected_hash = hashlib.sha256(
        request.wf_definition.model_dump_json(by_alias=False).encode()
    ).hexdigest()
    assert artifact.hash == expected_hash


def test_compose_artifact_invalid_type_raises_400() -> None:
    class _BadRequest:
        pass

    with pytest.raises(HTTPException) as exc_info:
        compose_artifact(_BadRequest(), TEST_CREATOR)  # type: ignore[arg-type]
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Execution Results — request body factory
# ---------------------------------------------------------------------------


def make_execution_result_request_body(**kwargs: Any) -> dict[str, Any]:
    """Return a JSON-serialisable dict for an ExecutionResultRequest with sensible defaults."""
    defaults: dict[str, Any] = {
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "artifact_id": "some-artifact-id",
        "inputs": [{"label": "a", "value": 1}, {"label": "b", "value": 2}],
        "outputs": "3",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Execution Results CRUD — create
# ---------------------------------------------------------------------------


def test_create_execution_result_returns_201(client: ApiClient) -> None:
    response = client.post(
        "/api/v1/execution_results", json=make_execution_result_request_body()
    )
    assert response.status_code == status.HTTP_201_CREATED
    result_id = response.json()["id"]
    assert isinstance(result_id, str)
    assert len(result_id) > 0


def test_create_duplicate_execution_result_returns_409(client: ApiClient) -> None:
    body = make_execution_result_request_body()
    client.post("/api/v1/execution_results", json=body)
    response = client.post("/api/v1/execution_results", json=body)
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_execution_result_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.post(
        "/api/v1/execution_results", json=make_execution_result_request_body()
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Execution Results CRUD — read
# ---------------------------------------------------------------------------


def test_read_execution_result_returns_200(client: ApiClient) -> None:
    result_id = client.post(
        "/api/v1/execution_results", json=make_execution_result_request_body()
    ).json()["id"]
    response = client.get(f"/api/v1/execution_results/{result_id}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["artifact_id"] == "some-artifact-id"
    assert body["creator_name"] == TEST_CREATOR.name


def test_read_execution_result_not_found_returns_404(client: ApiClient) -> None:
    response = client.get("/api/v1/execution_results/does-not-exist")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Execution Results CRUD — update
# ---------------------------------------------------------------------------


def test_update_execution_result_returns_updated_data(client: ApiClient) -> None:
    result_id = client.post(
        "/api/v1/execution_results", json=make_execution_result_request_body()
    ).json()["id"]
    updated_body = make_execution_result_request_body(outputs="99")
    response = client.put(f"/api/v1/execution_results/{result_id}", json=updated_body)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["outputs"] == "99"


def test_update_execution_result_not_found_returns_404(client: ApiClient) -> None:
    response = client.put(
        "/api/v1/execution_results/does-not-exist",
        json=make_execution_result_request_body(),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_execution_result_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.put(
        "/api/v1/execution_results/some-id",
        json=make_execution_result_request_body(),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Execution Results CRUD — delete
# ---------------------------------------------------------------------------


def test_delete_execution_result_returns_200_and_removes_result(
    client: ApiClient,
) -> None:
    result_id = client.post(
        "/api/v1/execution_results", json=make_execution_result_request_body()
    ).json()["id"]
    response = client.delete(f"/api/v1/execution_results/{result_id}")
    assert response.status_code == status.HTTP_200_OK
    assert "deleted" in response.json()["detail"].lower()
    assert (
        client.get(f"/api/v1/execution_results/{result_id}").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_delete_execution_result_not_found_returns_404(client: ApiClient) -> None:
    response = client.delete("/api/v1/execution_results/does-not-exist")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_execution_result_unauthenticated_returns_401(
    unauthed_client: ApiClient,
) -> None:
    response = unauthed_client.delete("/api/v1/execution_results/some-id")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Execution Results — list by artifact
# ---------------------------------------------------------------------------


def test_list_execution_results_by_artifact_returns_matching_results(
    client: ApiClient,
) -> None:
    client.post(
        "/api/v1/execution_results",
        json=make_execution_result_request_body(artifact_id="artifact-a"),
    )
    client.post(
        "/api/v1/execution_results",
        json=make_execution_result_request_body(
            artifact_id="artifact-b", inputs=[{"label": "x", "value": 5}]
        ),
    )
    response = client.get("/api/v1/artifacts/artifact-a/execution_results")
    assert response.status_code == status.HTTP_200_OK
    results = response.json()
    assert len(results) == 1
    assert results[0]["artifact_id"] == "artifact-a"


def test_list_execution_results_by_artifact_returns_empty_for_unknown(
    client: ApiClient,
) -> None:
    response = client.get("/api/v1/artifacts/unknown-artifact/execution_results")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# ---------------------------------------------------------------------------
# SPA fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/favicon.ico", True),
        ("/assets/index-abc123.js", True),
        ("/background.svg", True),
        ("/", False),
        ("/node/" + "a" * 64, False),
        ("/some/client/route", False),
    ],
)
def test_is_asset_path(path: str, expected: bool) -> None:
    assert is_asset_path(path) is expected


def test_missing_asset_404s_instead_of_serving_the_app_shell(
    client: ApiClient,
) -> None:
    """A missing asset must 404 honestly; answering 200 with index.html hides
    broken asset paths and makes browsers re-request /favicon.ico endlessly."""
    response = client.get("/favicon.ico")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "text/html" not in response.headers.get("content-type", "")
