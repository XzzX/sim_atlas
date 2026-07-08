"""Contract tests for FileSystemStorage."""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
import pytest

import sim_atlas.file_system_storage as fss
from sim_atlas.file_system_storage import FileSystemStorage
from sim_atlas.models import (
    AnnotationRequest,
    AnnotationResponse,
    Filter,
    FunctionResponse,
    Reference,
    WfDefinition,
    WfEdge,
    WfFunctionNode,
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
