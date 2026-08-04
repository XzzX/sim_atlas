"""Contract tests for FileSystemStorage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import sim_atlas.file_system_storage as fss
from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.models import (
    AnnotationRequest,
    AnnotationResponse,
    ArtifactType,
    ExecutionResultMetadata,
    Filter,
    FunctionResponse,
    IOValue,
    Reference,
    ScoredSearchResponse,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
    WorkflowResponse,
)

from .test_storage_interface import StorageContractTests, make_node, make_workflow


class TestFileSystemStorage(StorageContractTests):
    """Run the full StorageInterface contract against FileSystemStorage."""

    @pytest.fixture
    def storage(self) -> FileSystemStorage:
        s = FileSystemStorage(path=None)
        return s


class _FakeSettings:
    def __init__(self, *, embeddings: bool) -> None:
        self.embeddings_enabled = embeddings


def test_search_hybrid_falls_back_to_keyword_without_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no embedding provider, search_hybrid must keyword-search, never embed."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(name="special_fn", python_import="lib.special_fn")
    )

    monkeypatch.setattr(fss, "load_settings", lambda: _FakeSettings(embeddings=False))

    async def _boom(*_args: Any, **_kwargs: Any) -> np.ndarray:
        raise AssertionError("create_embedding must not be called")

    monkeypatch.setattr(fss, "create_embedding", _boom)

    response = asyncio.run(storage.search_hybrid("special_fn"))
    names = [item.node.name for item in response.results.data]
    assert "special_fn" in names


def test_search_hybrid_none_query_returns_filtered() -> None:
    """A missing query degrades to filter-only browse without touching embeddings."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(name="a", category="physics", source_code="def a(): pass")
    )
    storage.create_artifact(
        make_node(name="b", category="math", source_code="def b(): pass")
    )

    response = asyncio.run(storage.search_hybrid(None, Filter(category="physics")))
    names = [item.node.name for item in response.results.data]
    assert names == ["a"]


def test_used_by_shape_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    """`used_by` is populated identically by the keyword and hybrid paths."""
    storage = FileSystemStorage(path=None)
    fn = make_node(name="child_fn", source_code="def child_fn(): pass")
    storage.create_artifact(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_artifact(wf)

    keyword = storage.search("child_fn")
    kw_fn = next(
        i.node
        for i in keyword.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert kw_fn.used_by is not None
    assert any(ref.id == wf.id for ref in kw_fn.used_by)
    assert next(ref for ref in kw_fn.used_by if ref.id == wf.id).artifact_type == (
        ArtifactType.WORKFLOW
    )

    monkeypatch.setattr(fss, "load_settings", lambda: _FakeSettings(embeddings=True))

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.ones((len(documents), 3))

    monkeypatch.setattr(fss, "create_embedding", _fake_embed)

    hybrid = asyncio.run(storage.search_hybrid("child_fn"))
    hy_fn = next(
        i.node
        for i in hybrid.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert hy_fn.used_by is not None
    assert any(ref.id == wf.id for ref in hy_fn.used_by)


def test_used_by_count_reflects_usages_within_workflow() -> None:
    """`count` is how many times the function appears in that workflow's `uses`."""
    storage = FileSystemStorage(path=None)
    fn = make_node(name="child_fn", source_code="def child_fn(): pass")
    storage.create_artifact(fn)
    wf = make_workflow(
        name="parent_wf",
        uses=[
            Reference(label="child_fn", id=fn.id, count=1),
            Reference(label="child_fn", id=fn.id, count=1),
        ],
    )
    storage.create_artifact(wf)

    result = storage.search("child_fn")
    node = next(
        i.node
        for i in result.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert node.used_by is not None
    ref = next(r for r in node.used_by if r.id == wf.id)
    assert ref.count == 2  # noqa: PLR2004
    assert ref.artifact_type == ArtifactType.WORKFLOW


def test_connections_lists_other_artifacts_sorted_by_count() -> None:
    """`connections` lists the other artifacts wired to a port, sorted by count."""
    storage = FileSystemStorage(path=None)
    fn_a = make_node(
        name="fn_a",
        source_code="def fn_a(): pass",
        outputs=[AnnotationResponse(label="out")],
    )
    fn_b = make_node(
        name="fn_b",
        source_code="def fn_b(): pass",
        inputs=[AnnotationResponse(label="in")],
    )
    fn_c = make_node(
        name="fn_c",
        source_code="def fn_c(): pass",
        inputs=[AnnotationResponse(label="in")],
    )
    storage.create_artifact(fn_a)
    storage.create_artifact(fn_b)
    storage.create_artifact(fn_c)

    def a_node(node_id: str) -> WfFunctionNode:
        return WfFunctionNode(
            node_id=node_id,
            atlas_id=fn_a.id,
            inputs=[],
            outputs=[AnnotationRequest(label="out")],
        )

    def sink_node(node_id: str, atlas_id: str) -> WfFunctionNode:
        return WfFunctionNode(
            node_id=node_id,
            atlas_id=atlas_id,
            inputs=[AnnotationRequest(label="in")],
            outputs=[],
        )

    wf1 = make_workflow(
        name="wf1",
        wf_definition=WfDefinition(
            nodes=[a_node("a1"), sink_node("b1", fn_b.id)],
            edges=[
                WfEdge(
                    source_node="a1",
                    source_port="out",
                    target_node="b1",
                    target_port="in",
                )
            ],
        ),
    )
    wf2 = make_workflow(
        name="wf2",
        wf_definition=WfDefinition(
            nodes=[a_node("a2"), sink_node("b2", fn_b.id), sink_node("c2", fn_c.id)],
            edges=[
                WfEdge(
                    source_node="a2",
                    source_port="out",
                    target_node="b2",
                    target_port="in",
                ),
                WfEdge(
                    source_node="a2",
                    source_port="out",
                    target_node="c2",
                    target_port="in",
                ),
            ],
        ),
    )
    storage.create_artifact(wf1)
    storage.create_artifact(wf2)

    result = storage.search("fn_a")
    node = next(
        i.node
        for i in result.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "fn_a"
    )
    connections = node.outputs[0].connections
    assert connections is not None
    assert [(c.id, c.count) for c in connections] == [
        (fn_b.id, 2),
        (fn_c.id, 1),
    ]
    assert all(c.artifact_type == ArtifactType.FUNCTION for c in connections)


def test_read_artifact_populates_connections_and_used_by() -> None:
    """`read_artifact` (not just `search`) fills in `connections` and `used_by`."""
    storage = FileSystemStorage(path=None)
    fn_a = make_node(
        name="fn_a",
        source_code="def fn_a(): pass",
        outputs=[AnnotationResponse(label="out")],
    )
    fn_b = make_node(
        name="fn_b",
        source_code="def fn_b(): pass",
        inputs=[AnnotationResponse(label="in")],
    )
    storage.create_artifact(fn_a)
    storage.create_artifact(fn_b)

    wf = make_workflow(
        name="wf",
        uses=[Reference(label="fn_a", id=fn_a.id, count=1)],
        wf_definition=WfDefinition(
            nodes=[
                WfFunctionNode(
                    node_id="a1",
                    atlas_id=fn_a.id,
                    inputs=[],
                    outputs=[AnnotationRequest(label="out")],
                ),
                WfFunctionNode(
                    node_id="b1",
                    atlas_id=fn_b.id,
                    inputs=[AnnotationRequest(label="in")],
                    outputs=[],
                ),
            ],
            edges=[
                WfEdge(
                    source_node="a1",
                    source_port="out",
                    target_node="b1",
                    target_port="in",
                )
            ],
        ),
    )
    storage.create_artifact(wf)

    node = storage.read_artifact(fn_a.id)
    assert isinstance(node, FunctionResponse)
    assert node.used_by is not None
    assert any(ref.id == wf.id for ref in node.used_by)

    connections = node.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_b.id]


def test_fill_connections_populates_workflow_ports() -> None:
    """A workflow's own ports get `connections` filled too, not just functions."""
    storage = FileSystemStorage(path=None)
    fn_sink = make_node(
        name="fn_sink",
        source_code="def fn_sink(): pass",
        inputs=[AnnotationResponse(label="in")],
    )
    storage.create_artifact(fn_sink)

    inner_wf = make_workflow(name="inner_wf", outputs=[AnnotationResponse(label="y")])
    storage.create_artifact(inner_wf)

    outer_wf = make_workflow(
        name="outer_wf",
        wf_definition=WfDefinition(
            nodes=[
                WfFunctionNode(
                    node_id="w1",
                    atlas_id=inner_wf.id,
                    inputs=[],
                    outputs=[AnnotationRequest(label="y")],
                ),
                WfFunctionNode(
                    node_id="s1",
                    atlas_id=fn_sink.id,
                    inputs=[AnnotationRequest(label="in")],
                    outputs=[],
                ),
            ],
            edges=[
                WfEdge(
                    source_node="w1",
                    source_port="y",
                    target_node="s1",
                    target_port="in",
                )
            ],
        ),
    )
    storage.create_artifact(outer_wf)

    node = storage.read_artifact(inner_wf.id)
    assert isinstance(node, WorkflowResponse)
    connections = node.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_sink.id]


# ---------------------------------------------------------------------------
# Semantic scoring
# ---------------------------------------------------------------------------


def _embed_as(vector: list[float]) -> Any:
    """Return a `create_embedding` stub that always embeds to *vector*."""

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.vstack([np.array(vector, dtype=np.float32)] * len(documents))

    return _fake_embed


def test_search_semantic_ranks_by_cosine_similarity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Results are ordered by cosine similarity to the query embedding."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(
            name="aligned",
            source_code="def aligned(): pass",
            embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
        )
    )
    storage.create_artifact(
        make_node(
            name="diagonal",
            source_code="def diagonal(): pass",
            embedding=np.array([0.7, 0.7, 0.0], dtype=np.float32),
        )
    )
    storage.create_artifact(
        make_node(
            name="orthogonal",
            source_code="def orthogonal(): pass",
            embedding=np.array([0.0, 0.0, 1.0], dtype=np.float32),
        )
    )

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(storage.search_semantic("anything"))

    assert [item.node.name for item in response.results.data] == [
        "aligned",
        "diagonal",
        "orthogonal",
    ]
    scores = [item.score for item in response.results.data]
    assert scores[0] == pytest.approx(1.0, abs=1e-6)
    assert scores[1] == pytest.approx(0.70710678, abs=1e-6)
    assert scores[2] == pytest.approx(0.0, abs=1e-6)


def test_search_semantic_zero_norm_embedding_scores_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A zero vector scores exactly 0.0 rather than NaN."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(
            name="empty_vec",
            source_code="def empty_vec(): pass",
            embedding=np.zeros(3, dtype=np.float32),
        )
    )

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(storage.search_semantic("anything"))

    assert response.results.total_items == 1
    assert response.results.data[0].score == 0.0


def test_search_semantic_skips_unembedded_and_respects_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nodes without an embedding stay invisible, and filters still apply."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(
            name="embedded_physics",
            category="physics",
            source_code="def embedded_physics(): pass",
            embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
        )
    )
    storage.create_artifact(
        make_node(
            name="embedded_math",
            category="math",
            source_code="def embedded_math(): pass",
            embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
        )
    )
    storage.create_artifact(
        make_node(
            name="unembedded_physics",
            category="physics",
            source_code="def unembedded_physics(): pass",
        )
    )

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(
        storage.search_semantic("anything", Filter(category="physics"))
    )

    assert [item.node.name for item in response.results.data] == ["embedded_physics"]


def test_search_semantic_without_embedded_artifacts_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No embedded candidates yields an empty page, not a stacking error."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(make_node(name="plain", source_code="def plain(): pass"))

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(storage.search_semantic("anything"))

    assert response.results.total_items == 0
    assert response.results.data == []
    assert response.results.total_pages == 0


def test_search_hybrid_semantic_rank_is_stable_on_ties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equally similar nodes keep their insertion order in the semantic rank."""
    storage = FileSystemStorage(path=None)
    embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    for name in ("first_fn", "second_fn", "third_fn"):
        storage.create_artifact(
            make_node(
                name=name, source_code=f"def {name}(): pass", embedding=embedding.copy()
            )
        )

    monkeypatch.setattr(fss, "load_settings", lambda: _FakeSettings(embeddings=True))
    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    # a query that matches no keyword text, so ordering comes from the semantic rank alone
    response = asyncio.run(storage.search_hybrid("qqqzzz"))

    assert [item.node.name for item in response.results.data] == [
        "first_fn",
        "second_fn",
        "third_fn",
    ]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _execution_result(**kwargs: Any) -> ExecutionResultMetadata:
    defaults: dict[str, Any] = {
        "id": "run-1",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "creator_name": "Test Creator",
        "creator_email": "creator@example.com",
        "creation_timestamp": "2024-01-01T00:00:00",
        "artifact_id": "artifact-1",
        "inputs": [
            IOValue(label="text", value="abc"),
            IOValue(label="count", value=3),
            IOValue(label="ratio", value=1.5),
            IOValue(label="flag", value=True),
        ],
        "outputs": "{}",
        "hash": "run-1-hash",
    }
    defaults.update(kwargs)
    return ExecutionResultMetadata(**defaults)


def test_persistence_round_trip(tmp_path: Path) -> None:
    """Artifacts and execution results survive a reload from disk."""
    storage = FileSystemStorage(path=tmp_path)
    fn = make_node(name="persisted_fn", source_code="def persisted_fn(): pass")
    wf = make_workflow(name="persisted_wf")
    embedding = np.array([0.25, 0.5, 0.75], dtype=np.float32)
    embedded = make_node(
        name="embedded_fn",
        source_code="def embedded_fn(): pass",
        embedding=embedding,
    )
    storage.create_artifact(fn)
    storage.create_artifact(wf)
    storage.create_artifact(embedded)
    storage.create_execution_result(_execution_result(artifact_id=fn.id))

    reloaded = FileSystemStorage(path=tmp_path)

    assert reloaded.count() == 3  # noqa: PLR2004
    # compare via read_artifact on both sides so derived fields are filled alike
    assert reloaded.read_artifact(fn.id) == storage.read_artifact(fn.id)
    assert reloaded.read_artifact(wf.id) == storage.read_artifact(wf.id)
    assert reloaded.read_execution_result("run-1") == storage.read_execution_result(
        "run-1"
    )

    # embeddings must never be compared with ==; see the ndarray note in the plan
    reloaded_embedding = reloaded.read_artifact(embedded.id).embedding
    assert reloaded_embedding is not None
    assert np.array_equal(reloaded_embedding, embedding)


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    """The temp file used for the atomic rename does not survive the write."""
    storage = FileSystemStorage(path=tmp_path)
    storage.create_artifact(make_node(source_code="def tmp_check(): pass"))
    storage.create_execution_result(_execution_result())

    assert (tmp_path / FileSystemStorage.ARTIFACTS_FILENAME).exists()
    assert (tmp_path / FileSystemStorage.EXECUTION_RESULTS_FILENAME).exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_interrupted_write_leaves_previous_file_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A write that fails mid-serialisation must not damage the stored file."""
    storage = FileSystemStorage(path=tmp_path)
    keeper = make_node(name="keeper", source_code="def keeper(): pass")
    storage.create_artifact(keeper)
    artifacts_file = tmp_path / FileSystemStorage.ARTIFACTS_FILENAME
    before = artifacts_file.read_bytes()

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("serialisation failed")

    monkeypatch.setattr(fss.json, "dump", _boom)

    with pytest.raises(RuntimeError):
        storage.create_artifact(
            make_node(name="doomed", source_code="def doomed(): pass")
        )

    assert artifacts_file.read_bytes() == before
    reloaded = FileSystemStorage(path=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.exists(keeper.id)


def test_corrupt_artifacts_file_raises_instead_of_emptying_storage(
    tmp_path: Path,
) -> None:
    """A damaged file must fail loudly, never silently discard the catalog."""
    artifacts_file = tmp_path / FileSystemStorage.ARTIFACTS_FILENAME
    artifacts_file.write_text("{ not json")

    with pytest.raises(json.JSONDecodeError):
        FileSystemStorage(path=tmp_path)

    assert artifacts_file.read_text() == "{ not json"


# ---------------------------------------------------------------------------
# Search results hold the stored artifacts, so serialisation must strip embeddings
# ---------------------------------------------------------------------------


def _search_all_methods(
    storage: FileSystemStorage, query: str
) -> dict[str, ScoredSearchResponse]:
    return {
        "search": storage.search(query),
        "search_semantic": asyncio.run(storage.search_semantic(query)),
        "search_hybrid": asyncio.run(storage.search_hybrid(query)),
    }


@pytest.mark.parametrize("method", ["search", "search_semantic", "search_hybrid"])
def test_search_responses_never_serialize_embeddings(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ScoredSearchItem.node` is typed as the Response class, so embeddings are dropped."""
    storage = FileSystemStorage(path=None)
    storage.create_artifact(
        make_node(
            name="embedded_fn",
            source_code="def embedded_fn(): pass",
            embedding=np.arange(16, dtype=np.float32),
        )
    )
    storage.create_artifact(
        make_workflow(name="embedded_wf", embedding=np.arange(16, dtype=np.float32))
    )

    monkeypatch.setattr(fss, "load_settings", lambda: _FakeSettings(embeddings=True))
    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0] * 16))

    response = _search_all_methods(storage, "embedded")[method]

    assert response.results.total_items > 0
    payload = response.model_dump_json()
    assert "embedding" not in payload
    assert "dtype" not in payload


def test_search_semantic_populates_used_by_and_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parity with the keyword and hybrid paths (ADR-0018)."""
    storage = FileSystemStorage(path=None)
    fn = make_node(
        name="child_fn",
        source_code="def child_fn(): pass",
        embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
    )
    storage.create_artifact(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_artifact(wf)

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(storage.search_semantic("anything"))
    node = next(
        i.node
        for i in response.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert node.used_by is not None
    assert [ref.id for ref in node.used_by] == [wf.id]


def test_search_semantic_does_not_return_stale_used_by(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search results alias the stored artifacts, so derived fields must be refreshed."""
    storage = FileSystemStorage(path=None)
    fn = make_node(
        name="child_fn",
        source_code="def child_fn(): pass",
        embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
    )
    storage.create_artifact(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_artifact(wf)

    # stamps used_by onto the stored artifact
    storage.search("child_fn")
    storage.delete_artifact(wf.id)

    monkeypatch.setattr(fss, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(storage.search_semantic("anything"))
    node = next(
        i.node
        for i in response.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert node.used_by is None
