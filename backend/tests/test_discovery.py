"""Tests for the search and embedding policy above the storage seam."""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
import pytest

from sim_atlas import discovery
from sim_atlas.models import Filter, ScoredSearchResponse
from sim_atlas.storage.file_system_storage import FileSystemStorage

from .test_storage_interface import make_node


class _FakeSettings:
    def __init__(self, *, embeddings: bool) -> None:
        self.embeddings_enabled = embeddings


def _set_embeddings_enabled(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setattr(
        discovery, "load_settings", lambda: _FakeSettings(embeddings=enabled)
    )


def _forbid_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom(*_args: Any, **_kwargs: Any) -> np.ndarray:
        raise AssertionError("create_embedding must not be called")

    monkeypatch.setattr(discovery, "create_embedding", _boom)


def _embed_as(vector: list[float]) -> Any:
    """A `create_embedding` stub that embeds every document to *vector*."""

    async def _fake_embed(
        documents: list[str], input_type: str = "document"
    ) -> np.ndarray:
        return np.vstack([np.array(vector, dtype=np.float32)] * len(documents))

    return _fake_embed


# ---------------------------------------------------------------------------
# search: hybrid vs. keyword routing (ADR-0018)
# ---------------------------------------------------------------------------


def test_search_falls_back_to_keyword_without_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no embedding provider, search must keyword-search, never embed."""
    storage = FileSystemStorage(path=None)
    storage.create_node(make_node(name="special_fn", python_import="lib.special_fn"))
    _set_embeddings_enabled(monkeypatch, False)
    _forbid_embedding(monkeypatch)

    response = asyncio.run(discovery.search(storage, "special_fn"))

    assert "special_fn" in [item.node.name for item in response.results.data]


def test_keyword_fallback_matches_a_sentence_shaped_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The keyword-only path must serve the full sentences the MCP tools ask for.

    Whole-query substring matching returned nothing here, which left a
    zero-config deployment with a catalog its agent could never see.
    """
    storage = FileSystemStorage(path=None)
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
    _set_embeddings_enabled(monkeypatch, False)
    _forbid_embedding(monkeypatch)

    response = asyncio.run(
        discovery.search(
            storage,
            "compute the gradient of a temperature field on an unstructured mesh",
        )
    )

    assert response.results.data[0].node.name == "gradient_on_mesh"


@pytest.mark.parametrize("query", [None, "", "   "])
def test_blank_query_browses_by_filter_without_embedding(
    query: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = FileSystemStorage(path=None)
    storage.create_node(
        make_node(name="a", category="physics", source_code="def a(): pass")
    )
    storage.create_node(
        make_node(name="b", category="math", source_code="def b(): pass")
    )
    _set_embeddings_enabled(monkeypatch, True)
    _forbid_embedding(monkeypatch)

    response = asyncio.run(discovery.search(storage, query, Filter(category="physics")))

    assert [item.node.name for item in response.results.data] == ["a"]


def test_semantic_false_forces_keyword_even_with_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FileSystemStorage(path=None)
    storage.create_node(make_node(name="special_fn"))
    _set_embeddings_enabled(monkeypatch, True)
    _forbid_embedding(monkeypatch)

    response = asyncio.run(discovery.search(storage, "special_fn", semantic=False))

    assert [item.node.name for item in response.results.data] == ["special_fn"]


def test_search_with_embeddings_passes_the_query_embedding_to_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FileSystemStorage(path=None)
    _set_embeddings_enabled(monkeypatch, True)
    monkeypatch.setattr(discovery, "create_embedding", _embed_as([0.5, 0.5]))
    seen: dict[str, Any] = {}
    real = storage.search_hybrid

    def _spy(
        query: str, query_embedding: np.ndarray, *args: Any, **kwargs: Any
    ) -> ScoredSearchResponse:
        seen["query"] = query
        seen["embedding"] = query_embedding
        return real(query, query_embedding, *args, **kwargs)

    monkeypatch.setattr(storage, "search_hybrid", _spy)

    asyncio.run(discovery.search(storage, "heat capacity"))

    assert seen["query"] == "heat capacity"
    assert np.array_equal(seen["embedding"], np.array([0.5, 0.5], dtype=np.float32))


# ---------------------------------------------------------------------------
# embedding jobs
# ---------------------------------------------------------------------------


def test_enrich_embeds_described_nodes_through_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only nodes with a description are embedded, written via ``set_embeddings``."""
    storage = FileSystemStorage(path=None)
    described = make_node(
        name="described", source_code="def d(): pass", description="does things"
    )
    bare = make_node(name="bare", source_code="def b(): pass")
    storage.create_node(described)
    storage.create_node(bare)
    monkeypatch.setattr(discovery, "create_embedding", _embed_as([1.0, 2.0]))

    asyncio.run(discovery.enrich(storage))

    embedding = storage.read_node(described.id).embedding
    assert embedding is not None
    assert np.array_equal(embedding, np.array([1.0, 2.0], dtype=np.float32))
    assert storage.read_node(bare.id).embedding is None


def test_embed_missing_embeds_every_unembedded_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FileSystemStorage(path=None)
    bare = make_node(name="bare", source_code="def b(): pass")
    storage.create_node(bare)
    monkeypatch.setattr(discovery, "create_embedding", _embed_as([1.0, 2.0]))

    asyncio.run(discovery.embed_missing(storage))

    assert storage.read_node(bare.id).embedding is not None
