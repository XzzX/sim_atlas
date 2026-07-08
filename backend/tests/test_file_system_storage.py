"""Contract tests for FileSystemStorage."""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
import pytest

import sim_atlas.file_system_storage as fss
from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.models import Filter, FunctionResponse, Reference

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
    wf = make_workflow(name="parent_wf", uses=[Reference(label="child_fn", id=fn.id)])
    storage.create_artifact(wf)

    keyword = storage.search("child_fn")
    kw_fn = next(
        i.node
        for i in keyword.results.data
        if isinstance(i.node, FunctionResponse) and i.node.name == "child_fn"
    )
    assert kw_fn.used_by is not None
    assert any(ref.id == wf.id for ref in kw_fn.used_by)

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
