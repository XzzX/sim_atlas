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

import numpy as np
import pytest

from sim_atlas.models import (
    AnnotationRequest,
    AnnotationResponse,
    ArtifactType,
    Filter,
    FilterOptions,
    NodeMetadata,
    Reference,
    ScoredSearchResponse,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
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


# A query no node's text contains, so hybrid ordering comes from the semantic
# rank alone.
NO_KEYWORD_MATCH = "qqqzzz"


def _vec(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


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

    # -----------------------------------------------------------------------
    # get_filter_options
    # -----------------------------------------------------------------------

    def test_get_filter_options_on_empty_storage_returns_empty(
        self, storage: StorageInterface
    ) -> None:
        options = storage.get_filter_options()
        assert isinstance(options, FilterOptions)
        assert options.artifact_type == []
        assert options.author == []
        assert options.keywords == []
        assert options.datatypes == []
        assert options.units == []
        assert options.quantities == []

    def test_get_filter_options_includes_node_type(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node())
        options = storage.get_filter_options()
        assert ArtifactType.FUNCTION in options.artifact_type

    def test_get_filter_options_includes_author(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(author_name="Alice"))
        options = storage.get_filter_options()
        assert "Alice" in options.author

    def test_get_filter_options_includes_keywords(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(keywords=["energy", "force"]))
        options = storage.get_filter_options()
        assert "energy" in options.keywords
        assert "force" in options.keywords

    def test_get_filter_options_includes_category(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(category="physics>mechanics"))
        options = storage.get_filter_options()
        assert "physics" in options.category

    def test_get_filter_options_includes_input_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(datatype="float")]))
        options = storage.get_filter_options()
        assert "float" in options.datatypes

    def test_get_filter_options_includes_output_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(outputs=[AnnotationResponse(datatype="int")]))
        options = storage.get_filter_options()
        assert "int" in options.datatypes

    def test_get_filter_options_includes_units(self, storage: StorageInterface) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(unit="m/s")]))
        options = storage.get_filter_options()
        assert "m/s" in options.units

    def test_get_filter_options_includes_quantities(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(quantity="velocity")]))
        options = storage.get_filter_options()
        assert "velocity" in options.quantities

    def test_get_filter_options_merges_multiple_nodes(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                author_name="Alice",
                source_code="def alice(): pass",
            )
        )
        storage.create_node(
            make_node(
                author_name="Bob",
                source_code="def bob(): pass",
            )
        )
        options = storage.get_filter_options()
        assert "Alice" in options.author
        assert "Bob" in options.author
        assert ArtifactType.FUNCTION in options.artifact_type

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
        storage.create_node(make_node(name="a", source_code="def a(): pass"))
        storage.create_node(make_node(name="b", source_code="def b(): pass"))
        result = storage.search(None)
        assert result.results.total_items == 2  # noqa: PLR2004

    def test_search_result_has_correct_structure(
        self, storage: StorageInterface
    ) -> None:
        page_limit = 10
        storage.create_node(make_node(name="a"))
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
        storage.create_node(
            make_node(
                python_import="mypackage.mymodule", source_code="def match(): pass"
            )
        )
        storage.create_node(
            make_node(
                python_import="other.stuff",
                docstring="xyz",
                source_code="def other(): pass",
            )
        )
        result = storage.search("mypackage")
        imports = [
            item.node.python_import
            for item in result.results.data
            if item.node.artifact_type == ArtifactType.FUNCTION
        ]
        assert "mypackage.mymodule" in imports

    def test_search_filter_by_category(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(
                name="physics_node",
                category="physics",
                source_code="def physics(): pass",
            )
        )
        storage.create_node(
            make_node(name="math_node", category="math", source_code="def math(): pass")
        )
        result = storage.search(None, Filter(category="physics"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.category == "physics"

    def test_search_filter_by_type(self, storage: StorageInterface) -> None:
        storage.create_node(make_node(source_code="def func(): pass"))
        result = storage.search(None, Filter(artifact_type=[ArtifactType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.FUNCTION

    def test_search_filter_by_author(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(author_name="Alice", source_code="def alice(): pass")
        )
        storage.create_node(make_node(author_name="Bob", source_code="def bob(): pass"))
        result = storage.search(None, Filter(author=["Alice"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.author_name == "Alice"

    def test_search_filter_by_keywords(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(keywords=["simulation", "physics"], source_code="def a(): pass")
        )
        storage.create_node(
            make_node(keywords=["chemistry"], source_code="def b(): pass")
        )
        result = storage.search(None, Filter(keywords=["physics"]))
        assert result.results.total_items == 1

    def test_search_pagination_splits_results(self, storage: StorageInterface) -> None:
        limit_per_page = 2
        total_items = 5
        for i in range(total_items):
            storage.create_node(
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
            storage.create_node(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        last_page = storage.search(None, page=3, limit=2)
        assert len(last_page.results.data) == 1

    def test_search_pagination_beyond_last_page_returns_empty(
        self, storage: StorageInterface
    ) -> None:
        for i in range(3):
            storage.create_node(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        beyond = storage.search(None, page=10, limit=5)
        assert len(beyond.results.data) == 0
        assert beyond.results.total_items == 3  # noqa: PLR2004

    def test_search_filter_port_type_inputs_matches_input_datatype(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="input_float",
                inputs=[AnnotationResponse(datatype="float")],
                outputs=[AnnotationResponse(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create_node(
            make_node(
                name="output_float",
                inputs=[AnnotationResponse(datatype="int")],
                outputs=[AnnotationResponse(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="inputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "input_float"

    def test_search_filter_port_type_outputs_matches_output_datatype(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="input_float",
                inputs=[AnnotationResponse(datatype="float")],
                outputs=[AnnotationResponse(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create_node(
            make_node(
                name="output_float",
                inputs=[AnnotationResponse(datatype="int")],
                outputs=[AnnotationResponse(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="outputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "output_float"

    def test_search_filter_port_type_both_matches_either(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="input_float",
                inputs=[AnnotationResponse(datatype="float")],
                outputs=[AnnotationResponse(datatype="int")],
                source_code="def a(): pass",
            )
        )
        storage.create_node(
            make_node(
                name="output_float",
                inputs=[AnnotationResponse(datatype="int")],
                outputs=[AnnotationResponse(datatype="float")],
                source_code="def b(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"], port_type="both"))
        assert result.results.total_items == 2  # noqa: PLR2004

    # --- Option A: union decomposition in filter options ---

    def test_get_filter_options_decomposes_union_datatypes(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="int | float")],
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
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        options = storage.get_filter_options()
        assert "list[int]" in options.datatypes

    # --- Option C: structural matching in search filter ---

    def test_search_filter_union_member_matches_union_port(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="union_node",
                inputs=[AnnotationResponse(datatype="int | float")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["int"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "union_node"

    def test_search_filter_bare_generic_matches_parameterised(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="list_node",
                inputs=[AnnotationResponse(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["list"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "list_node"

    def test_search_filter_parameterised_no_match_different_arg(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="list[float]")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["list[int]"]))
        assert result.results.total_items == 0

    def test_search_filter_exact_match_regression(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="float_node",
                inputs=[AnnotationResponse(datatype="float")],
                source_code="def a(): pass",
            )
        )
        result = storage.search(None, Filter(datatypes=["float"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "float_node"

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
    # suggest: cheap type-ahead lookup
    # -----------------------------------------------------------------------

    def test_suggest_matches_a_name_prefix(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = storage.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy"]

    def test_suggest_matches_a_partial_word_inside_the_name(
        self, storage: StorageInterface
    ) -> None:
        """The reported regression: 'temp' must already find 'get_temperature'."""
        storage.create_node(
            make_node(name="get_temperature", source_code="def a(): pass")
        )
        results = storage.suggest("temp")
        assert [s.name for s in results] == ["get_temperature"]

    def test_suggest_matches_the_python_import(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(
                name="unrelated_name",
                python_import="ase.md.get_temperature",
                source_code="def a(): pass",
            )
        )
        results = storage.suggest("get_temperature")
        assert [s.name for s in results] == ["unrelated_name"]

    def test_suggest_is_case_insensitive(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = storage.suggest("CALC")
        assert [s.name for s in results] == ["calculate_energy"]

    def test_suggest_returns_the_node_id(self, storage: StorageInterface) -> None:
        created = storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = storage.suggest("calc")
        assert results[0].id == created.id

    def test_suggest_ranks_a_name_prefix_above_a_name_substring(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(name="attempt_calc", source_code="def a(): pass"))
        storage.create_node(
            make_node(name="calculate_energy", source_code="def b(): pass")
        )
        results = storage.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy", "attempt_calc"]

    def test_suggest_ranks_name_matches_above_import_matches(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="unrelated_name",
                python_import="lib.calculate_energy",
                source_code="def a(): pass",
            )
        )
        storage.create_node(
            make_node(name="calculate_energy", source_code="def b(): pass")
        )
        results = storage.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy", "unrelated_name"]

    def test_suggest_ignores_docstrings_and_descriptions(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(
                name="unrelated_name",
                python_import="lib.unrelated",
                docstring="Computes the calculation of interest.",
                brief_description="A calculation helper.",
                source_code="def a(): pass",
            )
        )
        assert storage.suggest("calc") == []

    def test_suggest_honours_limit(self, storage: StorageInterface) -> None:
        for i in range(5):
            storage.create_node(
                make_node(name=f"calc_{i}", source_code=f"def f{i}(): pass")
            )
        results = storage.suggest("calc", limit=2)
        assert len(results) == 2  # noqa: PLR2004

    def test_suggest_honours_filter(self, storage: StorageInterface) -> None:
        storage.create_node(
            make_node(
                name="calc_physics",
                category="physics",
                source_code="def a(): pass",
            )
        )
        storage.create_node(
            make_node(
                name="calc_chemistry",
                category="chemistry",
                source_code="def b(): pass",
            )
        )
        results = storage.suggest("calc", Filter(category="physics"))
        assert [s.name for s in results] == ["calc_physics"]

    def test_suggest_blank_query_returns_nothing(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        assert storage.suggest("") == []
        assert storage.suggest("   ") == []

    def test_suggest_empty_storage_returns_nothing(
        self, storage: StorageInterface
    ) -> None:
        assert storage.suggest("anything") == []

    def test_suggest_finds_workflows(self, storage: StorageInterface) -> None:
        wf = make_workflow(name="temperature_pipeline")
        storage.create_node(wf)
        results = storage.suggest("temperature")
        assert [s.name for s in results] == ["temperature_pipeline"]
        assert results[0].python_import is None
        assert results[0].artifact_type == ArtifactType.WORKFLOW

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

    def test_search_workflow_by_name(self, storage: StorageInterface) -> None:
        wf = make_workflow(name="my_pipeline")
        storage.create_node(wf)
        result = storage.search("my_pipeline")
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "my_pipeline"

    def test_filter_node_type_function_excludes_workflow(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        result = storage.search(None, Filter(artifact_type=[ArtifactType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.FUNCTION

    def test_filter_node_type_workflow_excludes_function(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        result = storage.search(None, Filter(artifact_type=[ArtifactType.WORKFLOW]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.WORKFLOW

    def test_get_filter_options_includes_both_node_types(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        options = storage.get_filter_options()
        assert ArtifactType.FUNCTION in options.artifact_type
        assert ArtifactType.WORKFLOW in options.artifact_type

    def test_search_drop_unmatched_false_ranks_without_excluding(
        self, storage: StorageInterface
    ) -> None:
        """A query must only order the filtered set, never shrink it.

        This is what find_by_signature needs: the annotation filters are the
        constraint, and a descriptive query is a tie-breaker on top of them.
        """
        storage.create_node(
            make_node(
                name="heat_capacity",
                source_code="def heat_capacity(): pass",
                outputs=[AnnotationResponse(label="c", datatype="float")],
            )
        )
        storage.create_node(
            make_node(
                name="lattice_constant",
                source_code="def lattice_constant(): pass",
                outputs=[AnnotationResponse(label="a", datatype="float")],
            )
        )
        float_outputs = Filter(datatypes=["float"], port_type="outputs")

        unqueried = storage.search(None, float_outputs)
        queried = storage.search(
            "the heat capacity of a solid", float_outputs, drop_unmatched=False
        )

        assert queried.results.total_items == unqueried.results.total_items == 2  # noqa: PLR2004
        assert queried.results.data[0].node.name == "heat_capacity"
        assert queried.results.data[1].score == 0.0

    def test_used_by_count_reflects_usages_within_workflow(
        self, storage: StorageInterface
    ) -> None:
        """`count` is how many times the function appears in that workflow's `uses`."""
        fn = make_node(name="child_fn", source_code="def child_fn(): pass")
        storage.create_node(fn)
        wf = make_workflow(
            name="parent_wf",
            uses=[
                Reference(label="child_fn", id=fn.id, count=1),
                Reference(label="child_fn", id=fn.id, count=1),
            ],
        )
        storage.create_node(wf)

        result = storage.search("child_fn")
        node = next(
            i.node
            for i in result.results.data
            if i.node.artifact_type == ArtifactType.FUNCTION
            and i.node.name == "child_fn"
        )
        assert node.used_by is not None
        ref = next(r for r in node.used_by if r.id == wf.id)
        assert ref.count == 2  # noqa: PLR2004
        assert ref.artifact_type == ArtifactType.WORKFLOW

    def test_connections_lists_other_nodes_sorted_by_count(
        self, storage: StorageInterface
    ) -> None:
        """`connections` lists the other nodes wired to a port, sorted by count."""
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
        storage.create_node(fn_a)
        storage.create_node(fn_b)
        storage.create_node(fn_c)

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
                nodes=[
                    a_node("a2"),
                    sink_node("b2", fn_b.id),
                    sink_node("c2", fn_c.id),
                ],
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
        storage.create_node(wf1)
        storage.create_node(wf2)

        result = storage.search("fn_a")
        node = next(
            i.node
            for i in result.results.data
            if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "fn_a"
        )
        connections = node.outputs[0].connections
        assert connections is not None
        assert [(c.id, c.count) for c in connections] == [
            (fn_b.id, 2),
            (fn_c.id, 1),
        ]
        assert all(c.artifact_type == ArtifactType.FUNCTION for c in connections)

    def test_read_node_populates_connections_and_used_by(
        self, storage: StorageInterface
    ) -> None:
        """`read_node` (not just `search`) fills in `connections` and `used_by`."""
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
        storage.create_node(fn_a)
        storage.create_node(fn_b)

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
        storage.create_node(wf)

        node = storage.read_node(fn_a.id)
        assert node.artifact_type == ArtifactType.FUNCTION
        assert node.used_by is not None
        assert any(ref.id == wf.id for ref in node.used_by)

        connections = node.outputs[0].connections
        assert connections is not None
        assert [c.id for c in connections] == [fn_b.id]

    def test_fill_connections_populates_workflow_ports(
        self, storage: StorageInterface
    ) -> None:
        """A workflow's own ports get `connections` filled too, not just functions."""
        fn_sink = make_node(
            name="fn_sink",
            source_code="def fn_sink(): pass",
            inputs=[AnnotationResponse(label="in")],
        )
        storage.create_node(fn_sink)

        inner_wf = make_workflow(
            name="inner_wf", outputs=[AnnotationResponse(label="y")]
        )
        storage.create_node(inner_wf)

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
        storage.create_node(outer_wf)

        node = storage.read_node(inner_wf.id)
        assert node.artifact_type == ArtifactType.WORKFLOW
        connections = node.outputs[0].connections
        assert connections is not None
        assert [c.id for c in connections] == [fn_sink.id]

    # -----------------------------------------------------------------------
    # search_hybrid: the caller supplies the query embedding
    # -----------------------------------------------------------------------

    def test_search_hybrid_ranks_by_similarity_without_keyword_hits(
        self, storage: StorageInterface
    ) -> None:
        for name, vector in (
            ("orthogonal", [0.0, 0.0, 1.0]),
            ("aligned", [1.0, 0.0, 0.0]),
            ("diagonal", [0.7, 0.7, 0.0]),
        ):
            storage.create_node(
                make_node(
                    name=name,
                    source_code=f"def {name}(): pass",
                    embedding=_vec(*vector),
                )
            )

        response = storage.search_hybrid(NO_KEYWORD_MATCH, _vec(1.0, 0.0, 0.0))

        assert [i.node.name for i in response.results.data] == [
            "aligned",
            "diagonal",
            "orthogonal",
        ]

    def test_search_hybrid_reaches_unembedded_nodes_through_keywords(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(
            make_node(name="special_fn", source_code="def special_fn(): pass")
        )
        response = storage.search_hybrid("special_fn", _vec(1.0, 0.0, 0.0))
        assert [i.node.name for i in response.results.data] == ["special_fn"]

    def test_search_hybrid_respects_filter_and_skips_unembedded_semantically(
        self, storage: StorageInterface
    ) -> None:
        for name, category, embedding in (
            ("embedded_physics", "physics", _vec(1.0, 0.0, 0.0)),
            ("embedded_math", "math", _vec(1.0, 0.0, 0.0)),
            ("unembedded_physics", "physics", None),
        ):
            storage.create_node(
                make_node(
                    name=name,
                    category=category,
                    source_code=f"def {name}(): pass",
                    embedding=embedding,
                )
            )

        response = storage.search_hybrid(
            NO_KEYWORD_MATCH, _vec(1.0, 0.0, 0.0), Filter(category="physics")
        )

        assert [i.node.name for i in response.results.data] == ["embedded_physics"]

    def test_search_hybrid_with_no_candidates_returns_an_empty_page(
        self, storage: StorageInterface
    ) -> None:
        storage.create_node(make_node(name="plain", source_code="def plain(): pass"))

        response = storage.search_hybrid(NO_KEYWORD_MATCH, _vec(1.0, 0.0, 0.0))

        assert response.results.total_items == 0
        assert response.results.data == []
        assert response.results.total_pages == 0

    def test_search_hybrid_semantic_rank_is_stable_on_ties(
        self, storage: StorageInterface
    ) -> None:
        """Equally similar nodes keep their insertion order."""
        for name in ("first_fn", "second_fn", "third_fn"):
            storage.create_node(
                make_node(
                    name=name,
                    source_code=f"def {name}(): pass",
                    embedding=_vec(1.0, 0.0, 0.0),
                )
            )

        response = storage.search_hybrid(NO_KEYWORD_MATCH, _vec(1.0, 0.0, 0.0))

        assert [i.node.name for i in response.results.data] == [
            "first_fn",
            "second_fn",
            "third_fn",
        ]

    def test_used_by_is_filled_alike_by_keyword_and_hybrid_search(
        self, storage: StorageInterface
    ) -> None:
        fn = make_node(
            name="child_fn",
            source_code="def child_fn(): pass",
            embedding=_vec(1.0, 0.0, 0.0),
        )
        storage.create_node(fn)
        wf = make_workflow(
            name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
        )
        storage.create_node(wf)

        for response in (
            storage.search("child_fn"),
            storage.search_hybrid("child_fn", _vec(1.0, 0.0, 0.0)),
        ):
            hit = next(i.node for i in response.results.data if i.node.id == fn.id)
            assert hit.used_by is not None
            ref = next(r for r in hit.used_by if r.id == wf.id)
            assert ref.artifact_type == ArtifactType.WORKFLOW

    def test_used_by_reflects_the_catalog_at_read_time(
        self, storage: StorageInterface
    ) -> None:
        """Deleting a workflow removes it from later reads' ``used_by``."""
        fn = make_node(
            name="child_fn",
            source_code="def child_fn(): pass",
            embedding=_vec(1.0, 0.0, 0.0),
        )
        storage.create_node(fn)
        wf = make_workflow(
            name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
        )
        storage.create_node(wf)
        assert storage.read_node(fn.id).used_by is not None

        storage.delete_node(wf.id)

        assert storage.read_node(fn.id).used_by is None
        response = storage.search_hybrid(NO_KEYWORD_MATCH, _vec(1.0, 0.0, 0.0))
        assert [i.node.used_by for i in response.results.data] == [None]

    @pytest.mark.parametrize("method", ["search", "search_hybrid"])
    def test_search_responses_never_serialize_embeddings(
        self, storage: StorageInterface, method: str
    ) -> None:
        """``ScoredSearchItem.node`` is the Response type, so embeddings drop out."""
        embedding = np.arange(16, dtype=np.float32)
        storage.create_node(
            make_node(
                name="embedded_fn",
                source_code="def embedded_fn(): pass",
                embedding=embedding,
            )
        )
        storage.create_node(make_workflow(name="embedded_wf", embedding=embedding))

        response = (
            storage.search("embedded")
            if method == "search"
            else storage.search_hybrid("embedded", np.ones(16, dtype=np.float32))
        )

        assert response.results.total_items > 0
        payload = response.model_dump_json()
        assert "embedding" not in payload
        assert "dtype" not in payload

    # -----------------------------------------------------------------------
    # batch access for embedding jobs
    # -----------------------------------------------------------------------

    def test_nodes_returns_every_stored_node_in_insertion_order(
        self, storage: StorageInterface
    ) -> None:
        first = storage.create_node(make_node(source_code="def a(): pass"))
        second = storage.create_node(make_workflow())
        assert [n.id for n in storage.nodes()] == [first.id, second.id]

    def test_set_embeddings_stores_one_embedding_per_node(
        self, storage: StorageInterface
    ) -> None:
        a = storage.create_node(make_node(name="a", source_code="def a(): pass"))
        b = storage.create_node(make_node(name="b", source_code="def b(): pass"))

        storage.set_embeddings({a.id: _vec(1.0, 2.0)})

        stored = storage.read_node(a.id).embedding
        assert stored is not None
        assert np.array_equal(stored, _vec(1.0, 2.0))
        assert storage.read_node(b.id).embedding is None

    def test_set_embeddings_with_an_unknown_id_writes_nothing(
        self, storage: StorageInterface
    ) -> None:
        a = storage.create_node(make_node(name="a", source_code="def a(): pass"))
        with pytest.raises(KeyError):
            storage.set_embeddings({a.id: _vec(1.0), "missing": _vec(1.0)})
        assert storage.read_node(a.id).embedding is None
