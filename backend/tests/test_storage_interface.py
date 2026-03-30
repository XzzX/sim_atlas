"""
Contract tests for StorageInterface.

Every class that implements StorageInterface should pass all tests defined here.
To add contract tests for a new implementation, create a subclass of
``StorageContractTests`` (note: no ``Test`` prefix on the base class, so pytest
does not collect it directly) and override the ``storage`` fixture to yield a
freshly connected, empty instance of the implementation under test.

To enable the semantic search tests override ``semantic_search_mock`` fixture in
the subclass and apply the appropriate monkeypatch for the embedding backend.

Example::

    class TestMyStorage(StorageContractTests):
        @pytest.fixture
        def storage(self):
            s = MyStorage()
            s.connect()
            yield s
            s.close()

        @pytest.fixture
        def semantic_search_mock(self, monkeypatch):
            monkeypatch.setattr("mymodule.create_embedding", lambda q: [0.0])
"""

from __future__ import annotations

from typing import Any

import pytest

from app.models import (
    Annotation,
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeType,
    ScoredSearchResponse,
)
from app.storage import StorageInterface

# ---------------------------------------------------------------------------
# Test data factory
# ---------------------------------------------------------------------------


def make_node(**kwargs: Any) -> NodeMetadata:
    """Return a ``NodeMetadata`` instance with sensible defaults.

    Keyword arguments override any default field value so tests can focus on
    the field(s) they care about.
    """
    defaults: dict[str, Any] = {
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "creator_name": "Test Creator",
        "creator_email": "creator@example.com",
        "creation_timestamp": "2024-01-01T00:00:00",
        "name": "test_node",
        "node_type": NodeType.FUNCTION,
        "category": "test",
        "keywords": ["test"],
        "homepage_url": "",
        "documentation_url": "",
        "source_url": "",
        "python_import": "test.module",
        "dependencies": None,
        "source_code": "def test(): pass",
        "source_code_hash": "abc123",
        "docstring": "A test node",
        "ai_docstring": "",
        "inputs": [],
        "outputs": [],
        "embedding": None,
    }
    defaults.update(kwargs)
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
    # MutableMapping contract
    # -----------------------------------------------------------------------

    def test_initially_empty(self, storage: StorageInterface) -> None:
        assert len(storage) == 0

    def test_setitem_and_getitem_roundtrip(self, storage: StorageInterface) -> None:
        node = make_node()
        storage["key1"] = node
        assert storage["key1"] == node

    def test_getitem_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            _ = storage["nonexistent"]

    def test_delitem_removes_entry(self, storage: StorageInterface) -> None:
        storage["key1"] = make_node()
        del storage["key1"]
        assert "key1" not in storage

    def test_delitem_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            del storage["nonexistent"]

    def test_len_increases_on_insert(self, storage: StorageInterface) -> None:
        assert len(storage) == 0
        storage["a"] = make_node(name="a")
        assert len(storage) == 1
        storage["b"] = make_node(name="b")
        assert len(storage) == 2  # noqa: PLR2004

    def test_len_decreases_on_delete(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(name="a")
        del storage["a"]
        assert len(storage) == 0

    def test_iter_yields_all_keys(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(name="a")
        storage["b"] = make_node(name="b")
        assert set(storage) == {"a", "b"}

    def test_contains_existing_key(self, storage: StorageInterface) -> None:
        storage["key1"] = make_node()
        assert "key1" in storage

    def test_contains_missing_key(self, storage: StorageInterface) -> None:
        assert "nonexistent" not in storage

    def test_keys_returns_all_keys(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(name="a")
        storage["b"] = make_node(name="b")
        assert set(storage.keys()) == {"a", "b"}

    def test_values_contains_inserted_node(self, storage: StorageInterface) -> None:
        node = make_node()
        storage["key1"] = node
        assert node in storage.values()

    def test_items_contains_key_value_pair(self, storage: StorageInterface) -> None:
        node = make_node()
        storage["key1"] = node
        assert ("key1", node) in storage.items()

    def test_get_existing_key_returns_node(self, storage: StorageInterface) -> None:
        node = make_node()
        storage["key1"] = node
        assert storage.get("key1") == node

    def test_get_missing_key_returns_none(self, storage: StorageInterface) -> None:
        assert storage.get("nonexistent") is None

    def test_get_missing_key_returns_custom_default(
        self, storage: StorageInterface
    ) -> None:
        sentinel = object()
        assert storage.get("nonexistent", sentinel) is sentinel

    def test_pop_removes_and_returns_node(self, storage: StorageInterface) -> None:
        node = make_node()
        storage["key1"] = node
        result = storage.pop("key1")
        assert result == node
        assert "key1" not in storage

    def test_overwrite_existing_key(self, storage: StorageInterface) -> None:
        node1 = make_node(name="first")
        node2 = make_node(name="second")
        storage["key1"] = node1
        storage["key1"] = node2
        assert storage["key1"] == node2
        assert len(storage) == 1

    # -----------------------------------------------------------------------
    # connect / close
    # -----------------------------------------------------------------------

    def test_connect_does_not_raise(self, storage: StorageInterface) -> None:
        storage.connect()

    def test_close_after_connect_does_not_raise(
        self, storage: StorageInterface
    ) -> None:
        storage.connect()
        storage.close()

    # -----------------------------------------------------------------------
    # get_filter_options
    # -----------------------------------------------------------------------

    def test_get_filter_options_on_empty_storage_returns_empty(
        self, storage: StorageInterface
    ) -> None:
        options = storage.get_filter_options()
        assert isinstance(options, FilterOptions)
        assert options.type == []
        assert options.author == []
        assert options.keywords == []
        assert options.datatypes == []
        assert options.units == []
        assert options.quantities == []

    def test_get_filter_options_includes_node_type(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(node_type=NodeType.FUNCTION)
        options = storage.get_filter_options()
        assert NodeType.FUNCTION in options.type

    def test_get_filter_options_includes_author(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(author_name="Alice")
        options = storage.get_filter_options()
        assert "Alice" in options.author

    def test_get_filter_options_includes_keywords(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(keywords=["energy", "force"])
        options = storage.get_filter_options()
        assert "energy" in options.keywords
        assert "force" in options.keywords

    def test_get_filter_options_includes_category(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(category="physics>mechanics")
        options = storage.get_filter_options()
        assert "physics" in options.category

    def test_get_filter_options_includes_input_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(inputs=[Annotation(datatype="float")])
        options = storage.get_filter_options()
        assert "float" in options.datatypes

    def test_get_filter_options_includes_output_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(outputs=[Annotation(datatype="int")])
        options = storage.get_filter_options()
        assert "int" in options.datatypes

    def test_get_filter_options_includes_units(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(inputs=[Annotation(unit="m/s")])
        options = storage.get_filter_options()
        assert "m/s" in options.units

    def test_get_filter_options_includes_quantities(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(inputs=[Annotation(quantity="velocity")])
        options = storage.get_filter_options()
        assert "velocity" in options.quantities

    def test_get_filter_options_merges_multiple_nodes(
        self, storage: StorageInterface
    ) -> None:
        storage["a"] = make_node(author_name="Alice", node_type=NodeType.FUNCTION)
        storage["b"] = make_node(author_name="Bob", node_type=NodeType.PYIRON_CORE_NODE)
        options = storage.get_filter_options()
        assert "Alice" in options.author
        assert "Bob" in options.author
        assert NodeType.FUNCTION in options.type
        assert NodeType.PYIRON_CORE_NODE in options.type

    # -----------------------------------------------------------------------
    # search
    # -----------------------------------------------------------------------

    def test_search_empty_storage_returns_empty_response(
        self, storage: StorageInterface
    ) -> None:
        result = storage.search(None)
        assert isinstance(result, ScoredSearchResponse)
        assert result.results.total_items == 0
        assert result.results.data == []

    def test_search_no_query_returns_all_nodes(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(name="a")
        storage["b"] = make_node(name="b")
        result = storage.search(None)
        assert result.results.total_items == 2  # noqa: PLR2004

    def test_search_result_has_correct_structure(
        self, storage: StorageInterface
    ) -> None:
        page_limit = 10
        storage["a"] = make_node(name="a")
        result = storage.search(None, limit=page_limit)
        assert result.results.page == 1
        assert result.results.limit == page_limit
        assert len(result.results.data) == 1
        item = result.results.data[0]
        assert item.score >= 0.0
        assert item.node.name == "a"

    def test_search_with_query_finds_matching_nodes(
        self, storage: StorageInterface
    ) -> None:
        storage["match"] = make_node(python_import="mypackage.mymodule")
        storage["other"] = make_node(python_import="other.stuff", docstring="xyz")
        result = storage.search("mypackage")
        imports = [item.node.python_import for item in result.results.data]
        assert "mypackage.mymodule" in imports

    def test_search_filter_by_category(self, storage: StorageInterface) -> None:
        storage["physics"] = make_node(name="physics_node", category="physics")
        storage["math"] = make_node(name="math_node", category="math")
        result = storage.search(None, Filter(category="physics"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.category == "physics"

    def test_search_filter_by_type(self, storage: StorageInterface) -> None:
        storage["func"] = make_node(node_type=NodeType.FUNCTION)
        storage["wf"] = make_node(node_type=NodeType.PYTHON_WORKFLOW_DEFINITION)
        result = storage.search(None, Filter(type=[NodeType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.node_type == NodeType.FUNCTION

    def test_search_filter_by_author(self, storage: StorageInterface) -> None:
        storage["alice_node"] = make_node(author_name="Alice")
        storage["bob_node"] = make_node(author_name="Bob")
        result = storage.search(None, Filter(author=["Alice"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.author_name == "Alice"

    def test_search_filter_by_keywords(self, storage: StorageInterface) -> None:
        storage["a"] = make_node(keywords=["simulation", "physics"])
        storage["b"] = make_node(keywords=["chemistry"])
        result = storage.search(None, Filter(keywords=["physics"]))
        assert result.results.total_items == 1

    def test_search_pagination_splits_results(self, storage: StorageInterface) -> None:
        limit_per_page = 2
        total_items = 5
        for i in range(total_items):
            storage[f"node_{i}"] = make_node(name=f"node_{i}")
        page1 = storage.search(None, page=1, limit=limit_per_page)
        page2 = storage.search(None, page=2, limit=limit_per_page)
        assert len(page1.results.data) == limit_per_page
        assert len(page2.results.data) == limit_per_page
        assert page1.results.total_items == total_items
        assert page1.results.total_pages == 3  # noqa: PLR2004
        assert page1.results.page == 1
        assert page2.results.page == 2  # noqa: PLR2004

    def test_search_pagination_last_page_is_partial(
        self, storage: StorageInterface
    ) -> None:
        for i in range(5):
            storage[f"node_{i}"] = make_node(name=f"node_{i}")
        last_page = storage.search(None, page=3, limit=2)
        assert len(last_page.results.data) == 1

    def test_search_pagination_beyond_last_page_returns_empty(
        self, storage: StorageInterface
    ) -> None:
        for i in range(3):
            storage[f"node_{i}"] = make_node(name=f"node_{i}")
        beyond = storage.search(None, page=10, limit=5)
        assert len(beyond.results.data) == 0
        assert beyond.results.total_items == 3  # noqa: PLR2004
