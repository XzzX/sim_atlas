"""
Contract tests for StorageInterface.

Every class that implements StorageInterface should pass all tests defined here.
To add contract tests for a new implementation, create a subclass of
``StorageContractTests`` (note: no ``Test`` prefix on the base class, so pytest
does not collect it directly) and override the ``storage`` fixture to yield a
freshly connected, empty instance of the implementation under test.

Example::

    class TestMyStorage(StorageContractTests):
        @pytest.fixture
        def storage(self):
            s = MyStorage()
            s.connect()
            yield s
            s.close()
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import pytest

from sim_atlas.models import (
    AnnotationRequest,
    AnnotationResponse,
    ArtifactType,
    NodeMetadata,
    WfDefinition,
    WfEdge,
    WfInputNode,
    WfOutputNode,
)
from sim_atlas.storage.storage_interface import (
    NodeAlreadyExistsError,
    NodeDuplicateError,
    StorageInterface,
)

# ---------------------------------------------------------------------------
# Test data factory
# ---------------------------------------------------------------------------


def make_node(**kwargs: Any) -> NodeMetadata:
    """Return a function-typed ``NodeMetadata`` instance with sensible defaults.

    Keyword arguments override any default field value so tests can focus on
    the field(s) they care about.
    """
    defaults: dict[str, Any] = {
        "artifact_type": ArtifactType.FUNCTION,
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "creator_name": "Test Creator",
        "creator_email": "creator@example.com",
        "creation_timestamp": "2024-01-01T00:00:00",
        "name": "test_node",
        "category": "test",
        "keywords": ["test"],
        "homepage_url": "",
        "documentation_url": "",
        "source_url": "",
        "python_import": "test.module",
        "dependencies": None,
        "source_code": "def test(): pass",
        "docstring": "A test node",
        "brief_description": "",
        "description": "",
        "inputs": [],
        "outputs": [],
        "embedding": None,
    }
    defaults.update(kwargs)
    if "id" not in defaults:
        defaults["id"] = str(uuid.uuid4())
    if "hash" not in defaults:
        defaults["hash"] = hashlib.sha256(
            defaults["source_code"].encode("utf-8")
        ).hexdigest()
    return NodeMetadata(**defaults)


def make_workflow(**kwargs: Any) -> NodeMetadata:
    """Return a workflow-typed ``NodeMetadata`` instance with sensible defaults."""
    defaults: dict[str, Any] = {
        "artifact_type": ArtifactType.WORKFLOW,
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "creator_name": "Test Creator",
        "creator_email": "creator@example.com",
        "creation_timestamp": "2024-01-01T00:00:00",
        "name": "test_workflow",
        "category": "test",
        "keywords": ["test"],
        "homepage_url": "",
        "documentation_url": "",
        "source_url": "",
        "source_code": "",
        "docstring": "A test workflow",
        "brief_description": "",
        "description": "",
        "inputs": [AnnotationResponse(label="x")],
        "outputs": [AnnotationResponse(label="y")],
        "embedding": None,
        "hash": "",
        "wf_definition": WfDefinition(
            nodes=[
                WfInputNode(node_id="i1", outputs=[AnnotationRequest(label="i1")]),
                WfOutputNode(node_id="o1", inputs=[AnnotationRequest(label="o1")]),
            ],
            edges=[WfEdge(source_node="i1", target_node="o1")],
        ),
    }
    defaults.update(kwargs)
    if "id" not in defaults:
        defaults["id"] = str(uuid.uuid4())
    return NodeMetadata(**defaults)


# ---------------------------------------------------------------------------
# Abstract contract test class
# ---------------------------------------------------------------------------


class StorageContractTests:
    """
    Abstract base class for contract-testing all ``StorageInterface``
    implementations.

    The ``storage`` fixture must be overridden by each concrete subclass.
    The storage instance it yields must be:

    * freshly connected (``connect()`` already called), and
    * empty (no nodes stored).

    Teardown (``close()``) should also be handled by the fixture.
    """

    @pytest.fixture
    def storage(self) -> StorageInterface:
        raise NotImplementedError("Subclasses must implement the `storage` fixture.")

    # -----------------------------------------------------------------------
    # CRUD contract
    # -----------------------------------------------------------------------

    def test_initially_empty(self, storage: StorageInterface) -> None:
        assert storage.count() == 0

    def test_create_and_read_roundtrip(self, storage: StorageInterface) -> None:
        node = make_node()
        created = storage.create_node(node)
        assert created == node
        assert storage.read_node(node.id) == node

    def test_read_missing_key_raises_key_error(self, storage: StorageInterface) -> None:
        with pytest.raises(KeyError):
            storage.read_node("nonexistent")

    def test_delete_removes_entry(self, storage: StorageInterface) -> None:
        node = make_node()
        storage.create_node(node)
        storage.delete_node(node.id)
        assert not storage.exists(node.id)

    def test_delete_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            storage.delete_node("nonexistent")

    def test_count_increases_on_create(self, storage: StorageInterface) -> None:
        assert storage.count() == 0
        storage.create_node(make_node(name="a", source_code="def a(): pass"))
        assert storage.count() == 1
        storage.create_node(make_node(name="b", source_code="def b(): pass"))
        assert storage.count() == 2  # noqa: PLR2004

    def test_count_decreases_on_delete(self, storage: StorageInterface) -> None:
        node = make_node(name="a")
        storage.create_node(node)
        storage.delete_node(node.id)
        assert storage.count() == 0

    def test_exists_returns_true_for_existing_key(
        self, storage: StorageInterface
    ) -> None:
        node = make_node()
        storage.create_node(node)
        assert storage.exists(node.id)

    def test_exists_returns_false_for_missing_key(
        self, storage: StorageInterface
    ) -> None:
        assert not storage.exists("nonexistent")

    def test_update_replaces_node(self, storage: StorageInterface) -> None:
        node1 = make_node(name="first")
        storage.create_node(node1)
        node2 = make_node(name="second")
        storage.update_node(node1.id, node2)
        assert storage.read_node(node1.id) == node2
        assert storage.count() == 1

    def test_update_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            storage.update_node("nonexistent", make_node())

    def test_create_duplicate_key_raises_value_error(
        self, storage: StorageInterface
    ) -> None:
        fixed_id = str(uuid.uuid4())
        storage.create_node(make_node(id=fixed_id))
        with pytest.raises(NodeAlreadyExistsError):
            storage.create_node(make_node(id=fixed_id))  # same id

    def test_nodes_returns_every_stored_node_in_insertion_order(
        self, storage: StorageInterface
    ) -> None:
        first = storage.create_node(make_node(source_code="def a(): pass"))
        second = storage.create_node(make_workflow())
        assert [n.id for n in storage.nodes()] == [first.id, second.id]

    def test_update_nodes_replaces_each_node_by_id(
        self, storage: StorageInterface
    ) -> None:
        a = storage.create_node(make_node(name="a", source_code="def a(): pass"))
        b = storage.create_node(make_node(name="b", source_code="def b(): pass"))
        storage.update_nodes(
            [a.model_copy(update={"name": "a2"}), b.model_copy(update={"name": "b2"})]
        )
        assert storage.read_node(a.id).name == "a2"
        assert storage.read_node(b.id).name == "b2"

    def test_update_nodes_with_a_missing_node_writes_nothing(
        self, storage: StorageInterface
    ) -> None:
        a = storage.create_node(make_node(name="a", source_code="def a(): pass"))
        with pytest.raises(KeyError):
            storage.update_nodes(
                [a.model_copy(update={"name": "a2"}), make_node(id="missing")]
            )
        assert storage.read_node(a.id).name == "a"

    # --- hash duplicate detection ---

    def test_create_raises_on_duplicate_source_hash(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(hash="abc123"))
        with pytest.raises(NodeDuplicateError):
            storage.create_node(make_node(hash="abc123"))

    def test_create_allows_duplicate_source_hash_when_check_disabled(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(hash="abc123"))
        # Should not raise
        storage.create_node(make_node(hash="abc123"), check_source_hash=False)
        assert storage.count() == 2  # noqa: PLR2004

    def test_create_empty_source_hash_never_triggers_hash_check(
        self, storage: StorageInterface
    ) -> None:
        # Two nodes with hash="" (the default) must not conflict
        storage.create_node(make_node(hash=""))
        storage.create_node(make_node(hash=""))
        assert storage.count() == 2  # noqa: PLR2004

    # -----------------------------------------------------------------------
    # Workflow node contract tests
    # -----------------------------------------------------------------------

    def test_create_and_read_workflow_roundtrip(
        self, storage: StorageInterface
    ) -> None:
        wf = make_workflow()
        created = storage.create_node(wf)
        assert created == wf
        result = storage.read_node(wf.id)
        assert result == wf
