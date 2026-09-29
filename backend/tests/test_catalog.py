"""Tests for Catalog: search, suggest, facets and hydrated reads."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import sim_atlas.catalog._catalog as catalog_module
from sim_atlas.catalog import Catalog
from sim_atlas.catalog._catalog import cosine_similarity
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
)
from sim_atlas.storage.file_system_storage import FileSystemStorage
from sim_atlas.storage.storage_interface import StorageInterface

from .test_storage_interface import make_node, make_workflow

# A query no node's text contains, so hybrid ordering comes from the semantic
# rank alone.
_NO_KEYWORD_MATCH = "qqqzzz"


def _enable_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        catalog_module, "load_settings", lambda: _FakeSettings(embeddings=True)
    )


class TestCatalog:
    """Search, facets and suggest over an in-memory storage adapter."""

    @pytest.fixture
    def storage(self) -> StorageInterface:
        return FileSystemStorage(path=None)

    @pytest.fixture
    def catalog(self, storage: StorageInterface) -> Catalog:
        return Catalog(storage)

    # -----------------------------------------------------------------------
    # get_filter_options
    # -----------------------------------------------------------------------

    def test_get_filter_options_on_empty_storage_returns_empty(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        options = catalog.get_filter_options()
        assert isinstance(options, FilterOptions)
        assert options.artifact_type == []
        assert options.author == []
        assert options.keywords == []
        assert options.datatypes == []
        assert options.units == []
        assert options.quantities == []

    def test_get_filter_options_includes_node_type(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node())
        options = catalog.get_filter_options()
        assert ArtifactType.FUNCTION in options.artifact_type

    def test_get_filter_options_includes_author(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(author_name="Alice"))
        options = catalog.get_filter_options()
        assert "Alice" in options.author

    def test_get_filter_options_includes_keywords(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(keywords=["energy", "force"]))
        options = catalog.get_filter_options()
        assert "energy" in options.keywords
        assert "force" in options.keywords

    def test_get_filter_options_includes_category(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(category="physics>mechanics"))
        options = catalog.get_filter_options()
        assert "physics" in options.category

    def test_get_filter_options_includes_input_datatypes(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(datatype="float")]))
        options = catalog.get_filter_options()
        assert "float" in options.datatypes

    def test_get_filter_options_includes_output_datatypes(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(outputs=[AnnotationResponse(datatype="int")]))
        options = catalog.get_filter_options()
        assert "int" in options.datatypes

    def test_get_filter_options_includes_units(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(unit="m/s")]))
        options = catalog.get_filter_options()
        assert "m/s" in options.units

    def test_get_filter_options_includes_quantities(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(inputs=[AnnotationResponse(quantity="velocity")]))
        options = catalog.get_filter_options()
        assert "velocity" in options.quantities

    def test_get_filter_options_merges_multiple_nodes(
        self, storage: StorageInterface, catalog: Catalog
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
        options = catalog.get_filter_options()
        assert "Alice" in options.author
        assert "Bob" in options.author
        assert ArtifactType.FUNCTION in options.artifact_type

    # -----------------------------------------------------------------------
    # search
    # -----------------------------------------------------------------------

    def test_search_empty_storage_returns_empty_response(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        result = catalog.search(None)
        assert isinstance(result, ScoredSearchResponse)
        assert result.results.total_items == 0
        assert result.results.data == []

    def test_search_no_query_returns_all_nodes(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(name="a", source_code="def a(): pass"))
        storage.create_node(make_node(name="b", source_code="def b(): pass"))
        result = catalog.search(None)
        assert result.results.total_items == 2  # noqa: PLR2004

    def test_search_result_has_correct_structure(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        page_limit = 10
        storage.create_node(make_node(name="a"))
        result = catalog.search(None, limit=page_limit)
        assert result.results.page == 1
        assert result.results.limit == page_limit
        assert len(result.results.data) == 1
        item = result.results.data[0]
        assert item.score >= 0.0
        assert item.node.name == "a"

    def test_search_with_query_finds_matching_nodes(
        self, storage: StorageInterface, catalog: Catalog
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
        result = catalog.search("mypackage")
        imports = [
            item.node.python_import
            for item in result.results.data
            if item.node.artifact_type == ArtifactType.FUNCTION
        ]
        assert "mypackage.mymodule" in imports

    def test_search_filter_by_category(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
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
        result = catalog.search(None, Filter(category="physics"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.category == "physics"

    def test_search_filter_by_type(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(source_code="def func(): pass"))
        result = catalog.search(None, Filter(artifact_type=[ArtifactType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.FUNCTION

    def test_search_filter_by_author(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(author_name="Alice", source_code="def alice(): pass")
        )
        storage.create_node(make_node(author_name="Bob", source_code="def bob(): pass"))
        result = catalog.search(None, Filter(author=["Alice"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.author_name == "Alice"

    def test_search_filter_by_keywords(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(keywords=["simulation", "physics"], source_code="def a(): pass")
        )
        storage.create_node(
            make_node(keywords=["chemistry"], source_code="def b(): pass")
        )
        result = catalog.search(None, Filter(keywords=["physics"]))
        assert result.results.total_items == 1

    def test_search_pagination_splits_results(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        limit_per_page = 2
        total_items = 5
        for i in range(total_items):
            storage.create_node(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        page1 = catalog.search(None, page=1, limit=limit_per_page)
        page2 = catalog.search(None, page=2, limit=limit_per_page)
        assert len(page1.results.data) == limit_per_page
        assert len(page2.results.data) == limit_per_page
        assert page1.results.total_items == total_items
        assert page1.results.total_pages == 3  # noqa: PLR2004
        assert page1.results.page == 1
        assert page2.results.page == 2  # noqa: PLR2004

    def test_search_pagination_last_page_is_partial(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        for i in range(5):
            storage.create_node(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        last_page = catalog.search(None, page=3, limit=2)
        assert len(last_page.results.data) == 1

    def test_search_pagination_beyond_last_page_returns_empty(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        for i in range(3):
            storage.create_node(
                make_node(name=f"node_{i}", source_code=f"def node_{i}(): pass")
            )
        beyond = catalog.search(None, page=10, limit=5)
        assert len(beyond.results.data) == 0
        assert beyond.results.total_items == 3  # noqa: PLR2004

    def test_search_filter_port_type_inputs_matches_input_datatype(
        self, storage: StorageInterface, catalog: Catalog
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
        result = catalog.search(None, Filter(datatypes=["float"], port_type="inputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "input_float"

    def test_search_filter_port_type_outputs_matches_output_datatype(
        self, storage: StorageInterface, catalog: Catalog
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
        result = catalog.search(None, Filter(datatypes=["float"], port_type="outputs"))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "output_float"

    def test_search_filter_port_type_both_matches_either(
        self, storage: StorageInterface, catalog: Catalog
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
        result = catalog.search(None, Filter(datatypes=["float"], port_type="both"))
        assert result.results.total_items == 2  # noqa: PLR2004

    # --- Option A: union decomposition in filter options ---

    def test_get_filter_options_decomposes_union_datatypes(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="int | float")],
                source_code="def a(): pass",
            )
        )
        options = catalog.get_filter_options()
        assert "int" in options.datatypes
        assert "float" in options.datatypes
        assert "int | float" not in options.datatypes

    def test_get_filter_options_keeps_generic_whole(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        options = catalog.get_filter_options()
        assert "list[int]" in options.datatypes

    # --- Option C: structural matching in search filter ---

    def test_search_filter_union_member_matches_union_port(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                name="union_node",
                inputs=[AnnotationResponse(datatype="int | float")],
                source_code="def a(): pass",
            )
        )
        result = catalog.search(None, Filter(datatypes=["int"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "union_node"

    def test_search_filter_bare_generic_matches_parameterised(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                name="list_node",
                inputs=[AnnotationResponse(datatype="list[int]")],
                source_code="def a(): pass",
            )
        )
        result = catalog.search(None, Filter(datatypes=["list"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "list_node"

    def test_search_filter_parameterised_no_match_different_arg(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                inputs=[AnnotationResponse(datatype="list[float]")],
                source_code="def a(): pass",
            )
        )
        result = catalog.search(None, Filter(datatypes=["list[int]"]))
        assert result.results.total_items == 0

    def test_search_filter_exact_match_regression(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                name="float_node",
                inputs=[AnnotationResponse(datatype="float")],
                source_code="def a(): pass",
            )
        )
        result = catalog.search(None, Filter(datatypes=["float"]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "float_node"

    # -----------------------------------------------------------------------
    # suggest: cheap type-ahead lookup
    # -----------------------------------------------------------------------

    def test_suggest_matches_a_name_prefix(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = catalog.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy"]

    def test_suggest_matches_a_partial_word_inside_the_name(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        """The reported regression: 'temp' must already find 'get_temperature'."""
        storage.create_node(
            make_node(name="get_temperature", source_code="def a(): pass")
        )
        results = catalog.suggest("temp")
        assert [s.name for s in results] == ["get_temperature"]

    def test_suggest_matches_the_python_import(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(
                name="unrelated_name",
                python_import="ase.md.get_temperature",
                source_code="def a(): pass",
            )
        )
        results = catalog.suggest("get_temperature")
        assert [s.name for s in results] == ["unrelated_name"]

    def test_suggest_is_case_insensitive(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = catalog.suggest("CALC")
        assert [s.name for s in results] == ["calculate_energy"]

    def test_suggest_returns_the_node_id(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        created = storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        results = catalog.suggest("calc")
        assert results[0].id == created.id

    def test_suggest_ranks_a_name_prefix_above_a_name_substring(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(name="attempt_calc", source_code="def a(): pass"))
        storage.create_node(
            make_node(name="calculate_energy", source_code="def b(): pass")
        )
        results = catalog.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy", "attempt_calc"]

    def test_suggest_ranks_name_matches_above_import_matches(
        self, storage: StorageInterface, catalog: Catalog
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
        results = catalog.suggest("calc")
        assert [s.name for s in results] == ["calculate_energy", "unrelated_name"]

    def test_suggest_ignores_docstrings_and_descriptions(
        self, storage: StorageInterface, catalog: Catalog
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
        assert catalog.suggest("calc") == []

    def test_suggest_honours_limit(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        for i in range(5):
            storage.create_node(
                make_node(name=f"calc_{i}", source_code=f"def f{i}(): pass")
            )
        results = catalog.suggest("calc", limit=2)
        assert len(results) == 2  # noqa: PLR2004

    def test_suggest_honours_filter(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
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
        results = catalog.suggest("calc", Filter(category="physics"))
        assert [s.name for s in results] == ["calc_physics"]

    def test_suggest_blank_query_returns_nothing(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(
            make_node(name="calculate_energy", source_code="def a(): pass")
        )
        assert catalog.suggest("") == []
        assert catalog.suggest("   ") == []

    def test_suggest_empty_storage_returns_nothing(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        assert catalog.suggest("anything") == []

    def test_suggest_finds_workflows(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        wf = make_workflow(name="temperature_pipeline")
        storage.create_node(wf)
        results = catalog.suggest("temperature")
        assert [s.name for s in results] == ["temperature_pipeline"]
        assert results[0].python_import is None
        assert results[0].artifact_type == ArtifactType.WORKFLOW

    # -----------------------------------------------------------------------
    # Workflow nodes
    # -----------------------------------------------------------------------

    def test_search_workflow_by_name(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        wf = make_workflow(name="my_pipeline")
        storage.create_node(wf)
        result = catalog.search("my_pipeline")
        assert result.results.total_items == 1
        assert result.results.data[0].node.name == "my_pipeline"

    def test_filter_node_type_function_excludes_workflow(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        result = catalog.search(None, Filter(artifact_type=[ArtifactType.FUNCTION]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.FUNCTION

    def test_filter_node_type_workflow_excludes_function(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        result = catalog.search(None, Filter(artifact_type=[ArtifactType.WORKFLOW]))
        assert result.results.total_items == 1
        assert result.results.data[0].node.artifact_type == ArtifactType.WORKFLOW

    def test_get_filter_options_includes_both_node_types(
        self, storage: StorageInterface, catalog: Catalog
    ) -> None:
        storage.create_node(make_node(source_code="def f(): pass"))
        storage.create_node(make_workflow())
        options = catalog.get_filter_options()
        assert ArtifactType.FUNCTION in options.artifact_type
        assert ArtifactType.WORKFLOW in options.artifact_type


class _FakeSettings:
    def __init__(self, *, embeddings: bool) -> None:
        self.embeddings_enabled = embeddings


def test_search_hybrid_falls_back_to_keyword_without_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no embedding provider, search_hybrid must keyword-search, never embed."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(make_node(name="special_fn", python_import="lib.special_fn"))

    monkeypatch.setattr(
        catalog_module, "load_settings", lambda: _FakeSettings(embeddings=False)
    )

    async def _boom(*_args: Any, **_kwargs: Any) -> np.ndarray:
        raise AssertionError("create_embedding must not be called")

    monkeypatch.setattr(catalog_module, "create_embedding", _boom)

    response = asyncio.run(catalog.search_hybrid("special_fn"))
    names = [item.node.name for item in response.results.data]
    assert "special_fn" in names


def test_search_hybrid_without_embeddings_matches_a_sentence_shaped_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The keyword-only path must serve the full sentences the MCP tools ask for.

    Whole-query substring matching returned nothing here, which left a
    zero-config deployment with a catalog its agent could never see.
    """
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(
        make_node(
            name="gradient_on_mesh",
            python_import="mylib.mesh.gradient_on_mesh",
            brief_description="Gradient of a scalar field on an unstructured mesh.",
            source_code="def gradient_on_mesh(): pass",
        )
    )
    storage.create_node(
        make_node(
            name="get_temperature",
            python_import="ase.md.get_temperature",
            brief_description="Instantaneous temperature of an atomic structure.",
            source_code="def get_temperature(): pass",
        )
    )

    monkeypatch.setattr(
        catalog_module, "load_settings", lambda: _FakeSettings(embeddings=False)
    )

    async def _boom(*_args: Any, **_kwargs: Any) -> np.ndarray:
        raise AssertionError("create_embedding must not be called")

    monkeypatch.setattr(catalog_module, "create_embedding", _boom)

    response = asyncio.run(
        catalog.search_hybrid(
            "compute the gradient of a temperature field on an unstructured mesh"
        )
    )

    assert [item.node.name for item in response.results.data][0] == "gradient_on_mesh"


def test_search_drop_unmatched_false_ranks_without_excluding() -> None:
    """A query must only order the filtered set, never shrink it.

    This is what find_by_signature needs: the annotation filters are the
    constraint, and a descriptive query is a tie-breaker on top of them.
    """
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
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

    unqueried = catalog.search(None, float_outputs)
    queried = catalog.search(
        "the heat capacity of a solid", float_outputs, drop_unmatched=False
    )

    assert queried.results.total_items == unqueried.results.total_items == 2  # noqa: PLR2004
    assert queried.results.data[0].node.name == "heat_capacity"
    assert queried.results.data[1].score == 0.0


def test_search_hybrid_none_query_returns_filtered() -> None:
    """A missing query degrades to filter-only browse without touching embeddings."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(
        make_node(name="a", category="physics", source_code="def a(): pass")
    )
    storage.create_node(
        make_node(name="b", category="math", source_code="def b(): pass")
    )

    response = asyncio.run(catalog.search_hybrid(None, Filter(category="physics")))
    names = [item.node.name for item in response.results.data]
    assert names == ["a"]


def test_used_by_shape_parity(monkeypatch: pytest.MonkeyPatch) -> None:
    """`used_by` is populated identically by the keyword and hybrid paths."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn = make_node(name="child_fn", source_code="def child_fn(): pass")
    storage.create_node(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_node(wf)

    keyword = catalog.search("child_fn")
    kw_fn = next(
        i.node
        for i in keyword.results.data
        if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "child_fn"
    )
    assert kw_fn.used_by is not None
    assert any(ref.id == wf.id for ref in kw_fn.used_by)
    assert next(ref for ref in kw_fn.used_by if ref.id == wf.id).artifact_type == (
        ArtifactType.WORKFLOW
    )

    monkeypatch.setattr(
        catalog_module, "load_settings", lambda: _FakeSettings(embeddings=True)
    )

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.ones((len(documents), 3))

    monkeypatch.setattr(catalog_module, "create_embedding", _fake_embed)

    hybrid = asyncio.run(catalog.search_hybrid("child_fn"))
    hy_fn = next(
        i.node
        for i in hybrid.results.data
        if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "child_fn"
    )
    assert hy_fn.used_by is not None
    assert any(ref.id == wf.id for ref in hy_fn.used_by)


def test_used_by_count_reflects_usages_within_workflow() -> None:
    """`count` is how many times the function appears in that workflow's `uses`."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
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

    result = catalog.search("child_fn")
    node = next(
        i.node
        for i in result.results.data
        if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "child_fn"
    )
    assert node.used_by is not None
    ref = next(r for r in node.used_by if r.id == wf.id)
    assert ref.count == 2  # noqa: PLR2004
    assert ref.artifact_type == ArtifactType.WORKFLOW


def test_connections_lists_other_nodes_sorted_by_count() -> None:
    """`connections` lists the other nodes wired to a port, sorted by count."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
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
    storage.create_node(wf1)
    storage.create_node(wf2)

    result = catalog.search("fn_a")
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


def test_read_node_populates_connections_and_used_by() -> None:
    """`read_node` (not just `search`) fills in `connections` and `used_by`."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
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

    node = catalog.read_node(fn_a.id)
    assert node.artifact_type == ArtifactType.FUNCTION
    assert node.used_by is not None
    assert any(ref.id == wf.id for ref in node.used_by)

    connections = node.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_b.id]


def test_fill_connections_populates_workflow_ports() -> None:
    """A workflow's own ports get `connections` filled too, not just functions."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn_sink = make_node(
        name="fn_sink",
        source_code="def fn_sink(): pass",
        inputs=[AnnotationResponse(label="in")],
    )
    storage.create_node(fn_sink)

    inner_wf = make_workflow(name="inner_wf", outputs=[AnnotationResponse(label="y")])
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

    node = catalog.read_node(inner_wf.id)
    assert node.artifact_type == ArtifactType.WORKFLOW
    connections = node.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_sink.id]


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

    monkeypatch.setattr(catalog_module, "WorkflowGraph", _boom)

    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(make_node(name="get_temperature", source_code="def a(): pass"))

    results = catalog.suggest("temp")
    assert [s.name for s in results] == ["get_temperature"]


def test_suggest_does_not_mutate_stored_nodes() -> None:
    """suggest must not stamp used_by/connections onto the stored objects."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
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

    catalog.suggest("temp")

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


def _assert_no_derived_fields(storage: StorageInterface) -> None:
    for node in storage.nodes():
        assert node.used_by is None
        for port in node.inputs + node.outputs:
            assert port.connections is None


def test_read_paths_do_not_mutate_stored_nodes() -> None:
    """read_node and search hand out hydrated copies; stored nodes stay bare."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn_a, fn_b, _ = _wired_catalog(storage)

    assert catalog.read_node(fn_a.id).used_by is not None
    hits = catalog.search("fn_b").results.data
    assert any(i.node.id == fn_b.id and i.node.used_by for i in hits)

    _assert_no_derived_fields(storage)


def test_read_node_returns_an_independent_copy() -> None:
    """Mutating one read's result must not leak into the next read."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn_a, fn_b, _ = _wired_catalog(storage)

    first = catalog.read_node(fn_a.id)
    first.used_by = None
    first.outputs[0].connections = None

    second = catalog.read_node(fn_a.id)
    assert second is not first
    assert second.used_by is not None
    connections = second.outputs[0].connections
    assert connections is not None
    assert [c.id for c in connections] == [fn_b.id]


def test_derived_fields_are_not_persisted(tmp_path: Path) -> None:
    """Reads followed by a write never put used_by/connections on disk."""
    storage = FileSystemStorage(path=tmp_path)
    catalog = Catalog(storage)
    fn_a, _, _ = _wired_catalog(storage)
    catalog.read_node(fn_a.id)
    catalog.search("fn")
    storage.create_node(make_node(name="later", source_code="def later(): pass"))

    data = json.loads((tmp_path / FileSystemStorage.NODES_FILENAME).read_text())
    for node in data.values():
        assert node["used_by"] is None
        for port in node["inputs"] + node["outputs"]:
            assert port["connections"] is None


def _embed_as(vector: list[float]) -> Any:
    """Return a `create_embedding` stub that always embeds to *vector*."""

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.vstack([np.array(vector, dtype=np.float32)] * len(documents))

    return _fake_embed


def test_search_hybrid_semantic_leg_skips_unembedded_and_respects_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unembedded nodes get no semantic rank, and filters still apply."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(
        make_node(
            name="embedded_physics",
            category="physics",
            source_code="def embedded_physics(): pass",
            embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
        )
    )
    storage.create_node(
        make_node(
            name="embedded_math",
            category="math",
            source_code="def embedded_math(): pass",
            embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
        )
    )
    storage.create_node(
        make_node(
            name="unembedded_physics",
            category="physics",
            source_code="def unembedded_physics(): pass",
        )
    )

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(
        catalog.search_hybrid(_NO_KEYWORD_MATCH, Filter(category="physics"))
    )

    assert [item.node.name for item in response.results.data] == ["embedded_physics"]


def test_search_hybrid_semantic_leg_without_embedded_nodes_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No embedded candidates and no keyword hit yields an empty page."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(make_node(name="plain", source_code="def plain(): pass"))

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(catalog.search_hybrid(_NO_KEYWORD_MATCH))

    assert response.results.total_items == 0
    assert response.results.data == []
    assert response.results.total_pages == 0


def test_search_hybrid_semantic_rank_is_stable_on_ties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equally similar nodes keep their insertion order in the semantic rank."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    for name in ("first_fn", "second_fn", "third_fn"):
        storage.create_node(
            make_node(
                name=name, source_code=f"def {name}(): pass", embedding=embedding.copy()
            )
        )

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(catalog.search_hybrid(_NO_KEYWORD_MATCH))

    assert [item.node.name for item in response.results.data] == [
        "first_fn",
        "second_fn",
        "third_fn",
    ]


@pytest.mark.parametrize("method", ["search", "search_hybrid"])
def test_search_responses_never_serialize_embeddings(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ScoredSearchItem.node` is typed as the Response class, so embeddings are dropped."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    storage.create_node(
        make_node(
            name="embedded_fn",
            source_code="def embedded_fn(): pass",
            embedding=np.arange(16, dtype=np.float32),
        )
    )
    storage.create_node(
        make_workflow(name="embedded_wf", embedding=np.arange(16, dtype=np.float32))
    )

    monkeypatch.setattr(
        catalog_module, "load_settings", lambda: _FakeSettings(embeddings=True)
    )
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0] * 16))

    response = (
        catalog.search("embedded")
        if method == "search"
        else asyncio.run(catalog.search_hybrid("embedded"))
    )

    assert response.results.total_items > 0
    payload = response.model_dump_json()
    assert "embedding" not in payload
    assert "dtype" not in payload


def test_search_hybrid_semantic_leg_populates_used_by_and_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The semantic leg hydrates like the keyword path (ADR-0018)."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn = make_node(
        name="child_fn",
        source_code="def child_fn(): pass",
        embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
    )
    storage.create_node(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_node(wf)

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(catalog.search_hybrid(_NO_KEYWORD_MATCH))
    node = next(
        i.node
        for i in response.results.data
        if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "child_fn"
    )
    assert node.used_by is not None
    assert [ref.id for ref in node.used_by] == [wf.id]


def test_search_hybrid_semantic_leg_does_not_return_stale_used_by(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Derived fields reflect the catalog at read time, not an earlier read."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    fn = make_node(
        name="child_fn",
        source_code="def child_fn(): pass",
        embedding=np.array([1.0, 0.0, 0.0], dtype=np.float32),
    )
    storage.create_node(fn)
    wf = make_workflow(
        name="parent_wf", uses=[Reference(label="child_fn", id=fn.id, count=1)]
    )
    storage.create_node(wf)

    catalog.search("child_fn")
    storage.delete_node(wf.id)

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(catalog.search_hybrid(_NO_KEYWORD_MATCH))
    node = next(
        i.node
        for i in response.results.data
        if i.node.artifact_type == ArtifactType.FUNCTION and i.node.name == "child_fn"
    )
    assert node.used_by is None


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


def test_search_hybrid_semantic_leg_ranks_by_cosine_similarity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no keyword hit, results are ordered by similarity to the query."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    for name, vector in (
        ("aligned", [1.0, 0.0, 0.0]),
        ("diagonal", [0.7, 0.7, 0.0]),
        ("orthogonal", [0.0, 0.0, 1.0]),
    ):
        storage.create_node(
            make_node(
                name=name,
                source_code=f"def {name}(): pass",
                embedding=np.array(vector, dtype=np.float32),
            )
        )

    _enable_embeddings(monkeypatch)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 0.0, 0.0]))

    response = asyncio.run(catalog.search_hybrid(_NO_KEYWORD_MATCH))

    assert [item.node.name for item in response.results.data] == [
        "aligned",
        "diagonal",
        "orthogonal",
    ]


def test_enrich_writes_embeddings_through_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Embeddings land on the stored nodes via ``update_nodes``, not by mutation."""
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    described = make_node(
        name="described", source_code="def d(): pass", description="does things"
    )
    bare = make_node(name="bare", source_code="def b(): pass")
    storage.create_node(described)
    storage.create_node(bare)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 2.0]))

    asyncio.run(catalog.enrich())

    embedding = storage.read_node(described.id).embedding
    assert embedding is not None
    assert np.array_equal(embedding, np.array([1.0, 2.0], dtype=np.float32))
    assert storage.read_node(bare.id).embedding is None
    assert described.embedding is None  # the caller's object is untouched


def test_embed_missing_embeds_every_unembedded_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FileSystemStorage(path=None)
    catalog = Catalog(storage)
    bare = make_node(name="bare", source_code="def b(): pass")
    storage.create_node(bare)
    monkeypatch.setattr(catalog_module, "create_embedding", _embed_as([1.0, 2.0]))

    asyncio.run(catalog.embed_missing())

    assert storage.read_node(bare.id).embedding is not None
