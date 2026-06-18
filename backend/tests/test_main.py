"""HTTP-level tests for the main FastAPI app."""

from __future__ import annotations

import hashlib
from collections.abc import Generator
from math import ceil
from typing import Any, Protocol, cast

import httpx
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.main import app, compose_artifact, get_storage
from sim_atlas.models import (
    Annotation,
    ArtifactType,
    FunctionRequest,
    ScoredSearchResponse,
    SearchResults,
    WfEdge,
    WfInputNode,
    WfOutputNode,
    WorkflowDefinition,
    WorkflowRequest,
)
from sim_atlas.security import Creator, get_current_user

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

TEST_CREATOR = Creator(name="Test User", email="test@example.com")


class ApiClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> httpx.Response: ...
    def post(self, url: str, **kwargs: Any) -> httpx.Response: ...
    def put(self, url: str, **kwargs: Any) -> httpx.Response: ...
    def delete(self, url: str, **kwargs: Any) -> httpx.Response: ...


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
    return FileSystemStorage(filename=None)


@pytest.fixture
def client(storage: FileSystemStorage) -> Generator[ApiClient]:
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_current_user] = lambda: TEST_CREATOR
    with TestClient(app) as c:
        yield cast(ApiClient, c)
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(storage: FileSystemStorage) -> Generator[ApiClient]:
    app.dependency_overrides[get_storage] = lambda: storage
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
# Artifact CRUD — create
# ---------------------------------------------------------------------------


def test_create_function_artifact_returns_201(client: ApiClient) -> None:
    response = client.post("/api/v1/artifacts", json=make_function_request_body())
    assert response.status_code == status.HTTP_201_CREATED
    artifact_id = response.json()
    assert isinstance(artifact_id, str)
    assert len(artifact_id) > 0


def test_create_workflow_artifact_returns_201(client: ApiClient) -> None:
    response = client.post("/api/v1/artifacts", json=make_workflow_request_body())
    assert response.status_code == status.HTTP_201_CREATED
    artifact_id = response.json()
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
    ).json()
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
    ).json()
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
    ).json()
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
    response = client.post("/api/v1/search")
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()


def test_search_with_query_finds_matching_artifact(client: ApiClient) -> None:
    client.post("/api/v1/artifacts", json=make_function_request_body(name="special_fn"))
    response = client.post("/api/v1/search", params={"query": "special_fn"})
    assert response.status_code == status.HTTP_200_OK
    names = [item["node"]["name"] for item in response.json()["results"]["data"]]
    assert "special_fn" in names


def test_search_with_filter_returns_filtered_results(client: ApiClient) -> None:
    client.post(
        "/api/v1/artifacts",
        json=make_function_request_body(category="unique-cat"),
    )
    response = client.post("/api/v1/search", json={"category": "unique-cat"})
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
    response = client.post("/api/v1/search", params={"page": 1, "limit": page_size})
    assert response.status_code == status.HTTP_200_OK
    results = response.json()["results"]
    assert results["page"] == 1
    assert results["limit"] == page_size
    assert results["total_items"] == total_artifacts
    assert results["total_pages"] == ceil(total_artifacts / page_size)
    assert len(results["data"]) == page_size


# ---------------------------------------------------------------------------
# Async search (storage.search_hybrid monkeypatched)
# ---------------------------------------------------------------------------


def _empty_search_response() -> ScoredSearchResponse:
    return ScoredSearchResponse(
        results=SearchResults(data=[], page=1, limit=10, total_items=0, total_pages=0)
    )


def test_semantic_search_returns_200(
    client: ApiClient,
    storage: FileSystemStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_search_hybrid(*args: Any, **kwargs: Any) -> ScoredSearchResponse:
        return _empty_search_response()

    monkeypatch.setattr(storage, "search_hybrid", mock_search_hybrid)
    response = client.post("/api/v1/semantic_search", params={"query": "test"})
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()


def test_hybrid_search_returns_200(
    client: ApiClient,
    storage: FileSystemStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_search_hybrid(*args: Any, **kwargs: Any) -> ScoredSearchResponse:
        return _empty_search_response()

    monkeypatch.setattr(storage, "search_hybrid", mock_search_hybrid)
    response = client.post("/api/v1/hybrid_search", params={"query": "test"})
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()


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
    definition = WorkflowDefinition(
        nodes=[WfInputNode(id="i1", name="x"), WfOutputNode(id="o1", name="y")],
        edges=[WfEdge(source="i1", target="o1")],
    )
    request = WorkflowRequest(
        name="my_wf",
        category="pipeline",
        keywords=["wf"],
        source_code=definition.model_dump_json(),
        docstring="A workflow.",
        inputs=[Annotation(label="x")],
        outputs=[Annotation(label="y")],
        definition=definition,
    )
    creator = Creator(name="Dev", email="dev@example.com")

    artifact = compose_artifact(request, creator)

    assert artifact.creator_name == "Dev"
    assert len(artifact.id) > 0
    expected_hash = hashlib.sha256(
        definition.model_dump_json(by_alias=False).encode()
    ).hexdigest()
    assert artifact.hash == expected_hash


def test_compose_artifact_invalid_type_raises_400() -> None:
    class _BadRequest:
        pass

    with pytest.raises(HTTPException) as exc_info:
        compose_artifact(_BadRequest(), TEST_CREATOR)  # type: ignore[arg-type]
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
