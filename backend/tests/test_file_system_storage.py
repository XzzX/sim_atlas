"""Adapter tests for FileSystemStorage: the storage contract plus persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import sim_atlas.storage.file_system_storage as fss
from sim_atlas.models import AnnotationResponse, ExecutionResultMetadata, IOValue
from sim_atlas.storage.file_system_storage import FileSystemStorage

from .test_storage_interface import StorageContractTests, make_node, make_workflow


class TestFileSystemStorage(StorageContractTests):
    """Run the full StorageInterface contract against FileSystemStorage."""

    @pytest.fixture
    def storage(self) -> FileSystemStorage:
        s = FileSystemStorage(path=None)
        return s


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

    node = FileSystemStorage(path=tmp_path).read_node(fn.id)
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
