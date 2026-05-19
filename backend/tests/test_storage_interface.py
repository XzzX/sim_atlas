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

import uuid
from typing import Any

import pytest

from sim_atlas_backend.models import (
    Annotation,
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeType,
    ScoredSearchResponse,
)
from sim_atlas_backend.storage_interface import StorageInterface

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
        "docstring": "A test node",
        "ai_summary": "",
        "ai_description": "",
        "inputs": [],
        "outputs": [],
        "embedding": None,
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
        key = storage.create(node)
        assert key == node.id
        assert storage.read(key) == node

    def test_read_missing_key_raises_key_error(self, storage: StorageInterface) -> None:
        with pytest.raises(KeyError):
            storage.read("nonexistent")

    def test_delete_removes_entry(self, storage: StorageInterface) -> None:
        key = storage.create(make_node())
        storage.delete(key)
        assert not storage.exists(key)

    def test_delete_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            storage.delete("nonexistent")

    def test_count_increases_on_create(self, storage: StorageInterface) -> None:
        assert storage.count() == 0
        storage.create(make_node(name="a", source_code="def a(): pass"))
        assert storage.count() == 1
        storage.create(make_node(name="b", source_code="def b(): pass"))
        assert storage.count() == 2  # noqa: PLR2004

    def test_count_decreases_on_delete(self, storage: StorageInterface) -> None:
        key = storage.create(make_node(name="a"))
        storage.delete(key)
        assert storage.count() == 0

    def test_exists_returns_true_for_existing_key(
        self, storage: StorageInterface
    ) -> None:
        key = storage.create(make_node())
        assert storage.exists(key)

    def test_exists_returns_false_for_missing_key(
        self, storage: StorageInterface
    ) -> None:
        assert not storage.exists("nonexistent")

    def test_update_replaces_node(self, storage: StorageInterface) -> None:
        node1 = make_node(name="first")
        key = storage.create(node1)
        node2 = make_node(name="second")
        storage.update(key, node2)
        assert storage.read(key) == node2
        assert storage.count() == 1

    def test_update_missing_key_raises_key_error(
        self, storage: StorageInterface
    ) -> None:
        with pytest.raises(KeyError):
            storage.update("nonexistent", make_node())

    def test_create_duplicate_key_raises_value_error(
        self, storage: StorageInterface
    ) -> None:
        fixed_id = str(uuid.uuid4())
        storage.create(make_node(id=fixed_id))
        with pytest.raises(ValueError):
            storage.create(make_node(id=fixed_id))  # same id

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
        storage.create(make_node(node_type=NodeType.FUNCTION))
        options = storage.get_filter_options()
        assert NodeType.FUNCTION in options.type

    def test_get_filter_options_includes_author(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(author_name="Alice"))
        options = storage.get_filter_options()
        assert "Alice" in options.author

    def test_get_filter_options_includes_keywords(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(keywords=["energy", "force"]))
        options = storage.get_filter_options()
        assert "energy" in options.keywords
        assert "force" in options.keywords

    def test_get_filter_options_includes_category(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(category="physics>mechanics"))
        options = storage.get_filter_options()
        assert "physics" in options.category

    def test_get_filter_options_includes_input_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(inputs=[Annotation(datatype="float")]))
        options = storage.get_filter_options()
        assert "float" in options.datatypes

    def test_get_filter_options_includes_output_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(outputs=[Annotation(datatype="int")]))
        options = storage.get_filter_options()
        assert "int" in options.datatypes

    def test_get_filter_options_includes_units(self, storage: StorageInterface) -> None:
        storage.create(make_node(inputs=[Annotation(unit="m/s")]))
        options = storage.get_filter_options()
        assert "m/s" in options.units

    def test_get_filter_options_includes_quantities(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(inputs=[Annotation(quantity="velocity")]))
        options = storage.get_filter_options()
        assert "velocity" in options.quantities

    def test_get_filter_options_merges_multiple_nodes(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                author_name="Alice",
                node_type=NodeType.FUNCTION,
                source_code="def alice(): pass",
            )
        )
        storage.create(
            make_node(
                author_name="Bob",
                node_type=NodeType.PYIRON_CORE_NODE,
                source_code="def bob(): pass",
            )
        )
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
        storage.create(make_node(name="a", source_code="def a(): pass"))
        storage.create(make_node(name="b", source_code="def b(): pass"))
        result = storage.search(None)
        assert result.results.total_items == 2  # noqa: PLR2004

    def test_search_result_has_correct_structure(
        self, storage: StorageInterface
    ) -> None:
        page_limit = 10
        storage.create(make_node(name="a"))
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
        storage.create(
            make_node(
                python_import="mypackage.mymodule", source_code="def match(): pass"
            )
        )
        storage.create(
            make_node(
                python_import="other.stuff",
                docstring="xyz",
                source_code="def other(): pass",
            )
        )
        result = storage.search("mypackage")
        imports = [item.node.python_import for item in result.results.data]
        assert "mypackage.mymodule" in imports

    def test_search_filter_by_category(self, storage: StorageInterface) -> None:
        storage.create(
            make_node(
                name="physics_node",
                category="physics",
                source_code="def physics(): pass",
            )
        )
        storage.create(
            make_node(name="math_node", category="math", source_code="def math(): pass")
        )
        result = storage.search(None, Filter(category="physics"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.category == "physics"

    def test_search_filter_by_type(self, storage: StorageInterface) -> None:
        storage.create(
            make_node(node_type=NodeType.FUNCTION, source_code="def func(): pass")
        )
        storage.create(
            make_node(
                node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
                source_code="def wf(): pass",
            )
        )
        result = storage.search(None, Filter(type=[NodeType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.node_type == NodeType.FUNCTION

    def test_search_filter_by_author(self, storage: StorageInterface) -> None:
        storage.create(make_node(author_name="Alice", source_code="def alice(): pass"))
        storage.create(make_node(author_name="Bob", source_code="def bob(): pass"))
        result = storage.search(None, Filter(author=["Alice"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.author_name == "Alice"

    def test_search_filter_by_keywords(self, storage: StorageInterface) -> None:
        storage.create(
            make_node(keywords=["simulation", "physics"], source_code="def a(): pass")
        )
        storage.create(make_node(keywords=["chemistry"], source_code="def b(): pass"))
        result = storage.search(None, Filter(keywords=["physics"]))
        assert result.results.total_items == 1

    def test_search_pagination_splits_results(self, storage: StorageInterface) -> None:
        limit_per_page = 2
        total_items = 5
        for i in range(total_items):
            storage.create(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
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
            storage.create(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        last_page = storage.search(None, page=3, limit=2)
        assert len(last_page.results.data) == 1

    def test_search_pagination_beyond_last_page_returns_empty(
        self, storage: StorageInterface
    ) -> None:
        for i in range(3):
            storage.create(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        beyond = storage.search(None, page=10, limit=5)
        assert len(beyond.results.data) == 0
        assert beyond.results.total_items == 3  # noqa: PLR2004

    def test_search_filter_port_type_inputs_matches_input_datatype(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="input_float",
                inputs=[Annotation(datatype="float")],
                outputs=[Annotation(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create(
            make_node(
                name="output_float",
                inputs=[Annotation(datatype="int")],
                outputs=[Annotation(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="inputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "input_float"

    def test_search_filter_port_type_outputs_matches_output_datatype(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="input_float",
                inputs=[Annotation(datatype="float")],
                outputs=[Annotation(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create(
            make_node(
                name="output_float",
                inputs=[Annotation(datatype="int")],
                outputs=[Annotation(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="outputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "output_float"

    def test_search_filter_port_type_both_matches_either(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="input_float",
                inputs=[Annotation(datatype="float")],
                outputs=[Annotation(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create(
            make_node(
                name="output_float",
                inputs=[Annotation(datatype="int")],
                outputs=[Annotation(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="both"))
        assert result.results.total_items == 2  # noqa: PLR2004

    # --- Option A: union decomposition in filter options ---

    def test_get_filter_options_decomposes_union_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                inputs=[Annotation(datatype="int | float")],
                source_code="def a(): pass",
            )
        )
        options = storage.get_filter_options()
        assert "int" in options.datatypes
        assert "float" in options.datatypes
        assert "int | float" not in options.datatypes

    def test_get_filter_options_keeps_generic_whole(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                inputs=[Annotation(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        options = storage.get_filter_options()
        assert "list[int]" in options.datatypes

    # --- Option C: structural matching in search filter ---

    def test_search_filter_union_member_matches_union_port(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="union_node",
                inputs=[Annotation(datatype="int | float")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["int"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "union_node"

    def test_search_filter_bare_generic_matches_parameterised(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="list_node",
                inputs=[Annotation(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["list"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "list_node"

    def test_search_filter_parameterised_no_match_different_arg(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                inputs=[Annotation(datatype="list[float]")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["list[int]"]))
        assert result.results.total_items == 0

    def test_search_filter_exact_match_regression(
        self, storage: StorageInterface
    ) -> None:
        storage.create(
            make_node(
                name="float_node",
                inputs=[Annotation(datatype="float")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "float_node"

    # --- source_code_hash duplicate detection ---

    def test_create_raises_on_duplicate_source_hash(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(source_code_hash="abc123"))
        with pytest.raises(ValueError):
            storage.create(make_node(source_code_hash="abc123"))

    def test_create_allows_duplicate_source_hash_when_check_disabled(
        self, storage: StorageInterface
    ) -> None:
        storage.create(make_node(source_code_hash="abc123"))
        # Should not raise
        storage.create(make_node(source_code_hash="abc123"), check_source_hash=False)
        assert storage.count() == 2  # noqa: PLR2004

    def test_create_empty_source_hash_never_triggers_hash_check(
        self, storage: StorageInterface
    ) -> None:
        # Two nodes with source_code_hash="" (the default) must not conflict
        storage.create(make_node(source_code_hash=""))
        storage.create(make_node(source_code_hash=""))
        assert storage.count() == 2  # noqa: PLR2004
