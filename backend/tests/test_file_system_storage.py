"""Contract tests for FileSystemStorage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import sim_atlas.storage.file_system_storage as fss
from sim_atlas.models import (
    AnnotationRequest,
    AnnotationResponse,
    ArtifactType,
    ExecutionResultMetadata,
    IOValue,
    NodeMetadata,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
)
from sim_atlas.storage._in_memory_search import cosine_similarity
from sim_atlas.storage.file_system_storage import FileSystemStorage

from .test_storage_interface import StorageContractTests, make_node, make_workflow


class TestFileSystemStorage(StorageContractTests):
    """Run the full StorageInterface contract against FileSystemStorage."""

    @pytest.fixture
    def storage(self) -> FileSystemStorage:
        s = FileSystemStorage(path=None)
        return s


def test_suggest_does_not_enrich_or_touch_the_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """suggest must not go through the used_by/connections hydration at all.

    This is the regression guard against someone "simplifying" suggest into a
    call to search: those enrichment steps are O(N·(V+E)) per port and are
    exactly what makes the hybrid path too slow to be the type-ahead path.
    """

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("suggest must not call this")

    monkeypatch.setattr(FileSystemStorage, "_hydrate", _boom)

    storage = FileSystemStorage(path=None)
    storage.create_node(make_node(name="get_temperature", source_code="def a(): pass"))

    results = storage.suggest("temp")
    assert [s.name for s in results] == ["get_temperature"]


def test_suggest_does_not_mutate_stored_nodes() -> None:
    """suggest must not stamp used_by/connections onto the stored objects."""
    storage = FileSystemStorage(path=None)
    fn = make_node(
        name="get_temperature",
        source_code="def a(): pass",
        inputs=[AnnotationResponse(label="atoms")],
    )
    storage.create_node(fn)
    wf = make_workflow(
        name="temperature_pipeline",
        uses=[Reference(label="get_temperature", id=fn.id, count=1)],
    )
    storage.create_node(wf)

    storage.suggest("temp")

    stored = next(node for node in storage.nodes() if node.id == fn.id)
    assert stored.artifact_type == ArtifactType.FUNCTION
    assert stored.used_by is None
    assert stored.inputs[0].connections is None


def _wired_catalog(
    storage: FileSystemStorage,
) -> tuple[NodeMetadata, NodeMetadata, NodeMetadata]:
    """Store fn_a -> fn_b wired inside a workflow; return (fn_a, fn_b, wf)."""
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
    wf = make_workflow(
        name="wf",
        uses=[
            Reference(label="fn_a", id=fn_a.id, count=1),
            Reference(label="fn_b", id=fn_b.id, count=1),
        ],
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
    for node in (fn_a, fn_b, wf):
        storage.create_node(node)
    return fn_a, fn_b, wf


def _assert_no_derived_fields(storage: FileSystemStorage) -> None:
    for node in storage.nodes():
        assert node.used_by is None
        for port in node.inputs + node.outputs:
            assert port.connections is None


def test_read_paths_do_not_mutate_stored_nodes() -> None:
    """read_node and search hand out hydrated copies; stored nodes stay bare."""
    storage = FileSystemStorage(path=None)
    fn_a, fn_b, _ = _wired_catalog(storage)

    assert storage.read_node(fn_a.id).used_by is not None
    hits = storage.search("fn_b").results.data
    assert any(i.node.id == fn_b.id and i.node.used_by for i in hits)

    _assert_no_derived_fields(storage)


def test_read_node_returns_an_independent_copy() -> None:
    """Mutating one read's result must not leak into the next read."""
    storage = FileSystemStorage(path=None)
    fn_a, fn_b, _ = _wired_catalog(storage)

    first = storage.read_node(fn_a.id)
    first.used_by = None
    first.outputs[0].connections = None

    second = storage.read_node(fn_a.id)
    assert second is not first
    assert second.used_by is not None
    connections = second.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_b.id]


def test_derived_fields_are_not_persisted(tmp_path: Path) -> None:
    """Reads followed by a write never put used_by/connections on disk."""
    storage = FileSystemStorage(path=tmp_path)
    fn_a, _, _ = _wired_catalog(storage)
    storage.read_node(fn_a.id)
    storage.search("fn")
    storage.create_node(make_node(name="later", source_code="def later(): pass"))

    data = json.loads((tmp_path / FileSystemStorage.NODES_FILENAME).read_text())
    for node in data.values():
        assert node["used_by"] is None
        for port in node["inputs"] + node["outputs"]:
            assert port["connections"] is None


def test_stale_derived_fields_on_disk_are_dropped_on_load(tmp_path: Path) -> None:
    """Files written before the fix may carry used_by; it must not be trusted."""
    storage = FileSystemStorage(path=tmp_path)
    fn = make_node(
        name="orphan",
        source_code="def orphan(): pass",
        inputs=[AnnotationResponse(label="x")],
    )
    storage.create_node(fn)

    nodes_file = tmp_path / FileSystemStorage.NODES_FILENAME
    data = json.loads(nodes_file.read_text())
    stale = {"label": "gone_wf", "id": "gone", "count": 1}
    data[fn.id]["used_by"] = [stale]
    data[fn.id]["inputs"][0]["connections"] = [stale]
    nodes_file.write_text(json.dumps(data))

    reloaded = FileSystemStorage(path=tmp_path)
    _assert_no_derived_fields(reloaded)
    node = reloaded.read_node(fn.id)
    assert node.used_by is None
    assert node.inputs[0].connections is None


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
    """Nodes and execution results survive a reload from disk."""
    storage = FileSystemStorage(path=tmp_path)
    fn = make_node(name="persisted_fn", source_code="def persisted_fn(): pass")
    wf = make_workflow(name="persisted_wf")
    embedding = np.array([0.25, 0.5, 0.75], dtype=np.float32)
    embedded = make_node(
        name="embedded_fn",
        source_code="def embedded_fn(): pass",
        embedding=embedding,
    )
    storage.create_node(fn)
    storage.create_node(wf)
    storage.create_node(embedded)
    storage.create_execution_result(_execution_result(artifact_id=fn.id))

    reloaded = FileSystemStorage(path=tmp_path)

    assert reloaded.count() == 3  # noqa: PLR2004
    # compare via read_node on both sides so derived fields are filled alike
    assert reloaded.read_node(fn.id) == storage.read_node(fn.id)
    assert reloaded.read_node(wf.id) == storage.read_node(wf.id)
    assert reloaded.read_execution_result("run-1") == storage.read_execution_result(
        "run-1"
    )

    # embeddings must never be compared with ==; see the ndarray note in the plan
    reloaded_embedding = reloaded.read_node(embedded.id).embedding
    assert reloaded_embedding is not None
    assert np.array_equal(reloaded_embedding, embedding)


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    """The temp file used for the atomic rename does not survive the write."""
    storage = FileSystemStorage(path=tmp_path)
    storage.create_node(make_node(source_code="def tmp_check(): pass"))
    storage.create_execution_result(_execution_result())

    assert (tmp_path / FileSystemStorage.NODES_FILENAME).exists()
    assert (tmp_path / FileSystemStorage.EXECUTION_RESULTS_FILENAME).exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_interrupted_write_leaves_previous_file_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A write that fails mid-serialisation must not damage the stored file."""
    storage = FileSystemStorage(path=tmp_path)
    keeper = make_node(name="keeper", source_code="def keeper(): pass")
    storage.create_node(keeper)
    nodes_file = tmp_path / FileSystemStorage.NODES_FILENAME
    before = nodes_file.read_bytes()

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("serialisation failed")

    monkeypatch.setattr(fss.json, "dump", _boom)

    with pytest.raises(RuntimeError):
        storage.create_node(make_node(name="doomed", source_code="def doomed(): pass"))

    assert nodes_file.read_bytes() == before
    reloaded = FileSystemStorage(path=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.exists(keeper.id)


def test_corrupt_nodes_file_raises_instead_of_emptying_storage(
    tmp_path: Path,
) -> None:
    """A damaged file must fail loudly, never silently discard the catalog."""
    nodes_file = tmp_path / FileSystemStorage.NODES_FILENAME
    nodes_file.write_text("{ not json")

    with pytest.raises(json.JSONDecodeError):
        FileSystemStorage(path=tmp_path)

    assert nodes_file.read_text() == "{ not json"


def test_cosine_similarity_of_known_vectors() -> None:
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(query, query) == pytest.approx(1.0, abs=1e-6)
    diagonal = np.array([0.7, 0.7, 0.0], dtype=np.float32)
    assert cosine_similarity(query, diagonal) == pytest.approx(0.70710678, abs=1e-6)
    orthogonal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    assert cosine_similarity(query, orthogonal) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_norm_scores_zero() -> None:
    """A zero vector scores exactly 0.0 rather than NaN."""
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(query, np.zeros(3, dtype=np.float32)) == 0.0
