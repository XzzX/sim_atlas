"""``run_pipeline`` behaviour, driven through fake two-phase parsers."""

import asyncio
import contextlib
import hashlib
from collections import Counter
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest
from sim_atlas_models import (
    AnnotationResponse,
    ArtifactType,
    ExecutionResultRequest,
    NodeRequest,
    NodeResponse,
    Reference,
)

from sim_atlas_toolkit import pipeline
from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeResult, NodeStoreError
from sim_atlas_toolkit.pipeline import GroupResult, run_pipeline
from sim_atlas_toolkit.plugin import (
    Description,
    Enrichment,
    Identity,
    NodeDraft,
    ResolvedChild,
)
from sim_atlas_toolkit.settings import ToolkitSettings

# _to_response builds a stored node exactly as MockNodeStore does, for seeding.
from .mock_api import MockNodeStore, _to_response  # pyright: ignore[reportPrivateUsage]


def _hash(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


@dataclass(eq=False)
class Obj:
    """A fake parseable object: one node (none for a container), with named
    children."""

    source: str
    children: dict[str, Any] = field(default_factory=dict[str, Any])
    container: bool = False

    @property
    def node_id(self) -> str:
        return _hash(self.source)


class FakeParser:
    """Parses ``Obj``; records every call and the children it was given."""

    name = "fake"

    def __init__(self, enrichment: Enrichment = Enrichment.NONE) -> None:
        self.enrichment = enrichment
        self.identified: Counter[str] = Counter()
        self.described: Counter[str] = Counter()
        self.seen_children: dict[str, Mapping[str, ResolvedChild]] = {}

    def identify(self, obj: Any) -> Identity | None:
        if not isinstance(obj, Obj):
            return None
        self.identified[obj.source] += 1
        node_id = None if obj.container else obj.node_id
        return Identity(node_id=node_id, children=obj.children)

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        assert isinstance(obj, Obj)
        self.described[obj.source] += 1
        self.seen_children[obj.source] = children
        if obj.container:
            return Description(node=None)
        request = NodeRequest.model_construct(
            id=obj.node_id,
            hash=obj.node_id,
            artifact_type=ArtifactType.FUNCTION,
            name=obj.source,
            category="test",
            keywords=[],
            source_code=obj.source,
            docstring="",
            inputs=[],
            outputs=[],
            uses=[
                Reference(label=label, id=child.id, count=1)
                for label, child in children.items()
            ],
        )
        return Description(node=NodeDraft(request, self.enrichment))


def _ctx(store: MockNodeStore, **settings: Any) -> ParseContext:
    return ParseContext(ToolkitSettings(embed=False, **settings), store)


async def test_single_object_is_created() -> None:
    store = MockNodeStore()

    result = await run_pipeline({"mod": [Obj("a")]}, [FakeParser()], _ctx(store))

    assert result == {"mod": GroupResult(created=1, existing=0, errors=0, unparsed=0)}
    assert [n.name for n in store.uploaded] == ["a"]


def _stored(store: MockNodeStore, obj: Obj) -> None:
    """Seed *obj*'s node as already stored."""
    store.preexisting(
        _to_response(
            NodeRequest(
                id=obj.node_id,
                hash=obj.node_id,
                artifact_type=ArtifactType.FUNCTION,
                name=obj.source,
                category="test",
                keywords=[],
                source_code=obj.source,
                docstring=f"Stored {obj.source}.",
                inputs=[],
                outputs=[],
            )
        )
    )


async def test_stored_node_is_not_described() -> None:
    store = MockNodeStore()
    a = Obj("a")
    _stored(store, a)
    parser = FakeParser()

    result = await run_pipeline({"mod": [a]}, [parser], _ctx(store))

    assert result == {"mod": GroupResult(created=0, existing=1, errors=0, unparsed=0)}
    assert parser.described == Counter()
    assert store.uploaded == []


async def test_stored_parents_children_are_not_identified() -> None:
    store = MockNodeStore()
    parent = Obj("parent", {"x": Obj("child", {"y": Obj("grandchild")})})
    _stored(store, parent)
    parser = FakeParser()

    await run_pipeline({"mod": [parent]}, [parser], _ctx(store))

    assert parser.identified == Counter({"parent": 1})


async def test_existence_is_checked_once_per_level() -> None:
    store = MockNodeStore()
    seeds = [Obj("a", {"x": Obj("a1"), "y": Obj("a2")}), Obj("b", {"x": Obj("b1")})]

    await run_pipeline({"mod": seeds}, [FakeParser()], _ctx(store))

    assert store.existing_ids_calls == [
        {o.node_id for o in seeds},
        {_hash("a1"), _hash("a2"), _hash("b1")},
    ]


async def test_parent_receives_created_and_stored_children() -> None:
    store = MockNodeStore()
    old = Obj("old")
    _stored(store, old)
    parent = Obj("parent", {"new": Obj("new"), "old": old})
    parser = FakeParser()

    result = await run_pipeline({"mod": [parent]}, [parser], _ctx(store))

    children = parser.seen_children["parent"]
    assert {label: c.name for label, c in children.items()} == {
        "new": "new",
        "old": "old",
    }
    assert children["old"].docstring == "Stored old."
    assert [n.name for n in store.uploaded] == ["new", "parent"]
    assert result == {"mod": GroupResult(created=2, existing=1, errors=0, unparsed=0)}


async def test_shared_child_is_processed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    llm_calls: list[str] = []

    async def fake_generate_docstring(
        ctx: ParseContext, source_code: str, docstring: str
    ) -> str:
        llm_calls.append(source_code)
        return docstring

    monkeypatch.setattr(pipeline, "generate_docstring", fake_generate_docstring)
    store = MockNodeStore()
    shared = Obj("shared")
    # A distinct object with identical content is the same node.
    twin = Obj("shared")
    seeds = [Obj("p1", {"c": shared}), Obj("p2", {"c": shared, "d": twin})]
    parser = FakeParser(Enrichment.FUNCTION)

    result = await run_pipeline({"mod": seeds}, [parser], _ctx(store))

    assert parser.identified["shared"] == 2  # noqa: PLR2004 - once per object
    assert parser.described["shared"] == 1
    assert sorted(llm_calls) == ["p1", "p2", "shared"]
    assert result == {"mod": GroupResult(created=3, existing=0, errors=0, unparsed=0)}


async def test_child_is_counted_in_first_group_reaching_it() -> None:
    store = MockNodeStore()
    shared = Obj("shared")
    seeds = {"first": [Obj("a", {"c": shared})], "second": [Obj("b", {"c": shared})]}

    result = await run_pipeline(seeds, [FakeParser()], _ctx(store))

    assert result == {
        "first": GroupResult(created=2, existing=0, errors=0, unparsed=0),
        "second": GroupResult(created=1, existing=0, errors=0, unparsed=0),
    }


async def test_unparsed_child_is_warned_and_omitted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = MockNodeStore()
    parent = Obj("parent", {"odd": 42, "ok": Obj("ok")})
    parser = FakeParser()

    result = await run_pipeline({"mod": [parent]}, [parser], _ctx(store))

    assert result == {"mod": GroupResult(created=2, existing=0, errors=0, unparsed=1)}
    assert "No parser available for 42 (child 'odd' of" in caplog.text
    assert set(parser.seen_children["parent"]) == {"ok"}
    (stored_parent,) = (n for n in store.uploaded if n.name == "parent")
    assert [r.label for r in stored_parent.uses] == ["ok"]


class LeakyParser(FakeParser):
    """Puts a response-side port (server-owned ``connections``) into a request."""

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        description = super().describe(obj, identity, children)
        if obj.source == "leaky" and description.node is not None:
            # The wrong type on purpose: this is the leak under test.
            leak = [AnnotationResponse(label="x", connections=[])]
            description.node.request.inputs = leak  # pyright: ignore[reportAttributeAccessIssue]
        return description


async def test_invalid_draft_never_reaches_the_store() -> None:
    store = MockNodeStore()
    parent = Obj("parent", {"c": Obj("leaky")})
    parser = LeakyParser()

    result = await run_pipeline({"mod": [parent]}, [parser], _ctx(store))

    assert [n.name for n in store.uploaded] == ["parent"]
    assert result == {"mod": GroupResult(created=1, existing=0, errors=1, unparsed=0)}
    # A failed child is unresolved for its parent.
    assert parser.seen_children["parent"] == {}


class MislabellingParser(FakeParser):
    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        description = super().describe(obj, identity, children)
        if description.node is not None:
            description.node.request.id = _hash("something else")
        return description


async def test_described_ids_must_match_identified_ids() -> None:
    store = MockNodeStore()

    result = await run_pipeline(
        {"mod": [Obj("a")]}, [MislabellingParser()], _ctx(store)
    )

    assert store.uploaded == []
    assert result == {"mod": GroupResult(created=0, existing=0, errors=1, unparsed=0)}


async def test_reference_cycle_is_an_error() -> None:
    store = MockNodeStore()
    a, b = Obj("a"), Obj("b")
    a.children["b"] = b
    b.children["a"] = a
    root = Obj("root", {"a": a})

    result = await run_pipeline({"mod": [root]}, [FakeParser()], _ctx(store))

    assert [n.name for n in store.uploaded] == ["root"]
    assert result == {"mod": GroupResult(created=1, existing=0, errors=2, unparsed=0)}


class _OverlapStore(MockNodeStore):
    """Holds each ``create_node`` open until *n* overlap (or a timeout)."""

    def __init__(self, n: int) -> None:
        super().__init__()
        self.n = n
        self.in_flight = 0
        self.peak = 0
        self.all_in_flight = asyncio.Event()

    async def create_node(self, node: NodeRequest) -> NodeResult:
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        if self.in_flight == self.n:
            self.all_in_flight.set()
        try:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.all_in_flight.wait(), timeout=1)
        finally:
            self.in_flight -= 1
        return await super().create_node(node)


async def test_independent_entries_run_concurrently() -> None:
    n = 3
    store = _OverlapStore(n)
    seeds = [Obj(str(i)) for i in range(n)]

    result = await run_pipeline(
        {"mod": seeds}, [FakeParser()], _ctx(store), concurrency=n
    )

    assert store.peak == n
    assert result == {"mod": GroupResult(created=n, existing=0, errors=0, unparsed=0)}


async def test_concurrency_bounds_entries_in_flight() -> None:
    store = _OverlapStore(3)
    seeds = [Obj(str(i)) for i in range(3)]

    await run_pipeline({"mod": seeds}, [FakeParser()], _ctx(store), concurrency=2)

    assert store.peak == 2  # noqa: PLR2004


async def test_container_child_is_not_warned_about(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = MockNodeStore()
    parent = Obj("parent", {"box": Obj("box", {"x": Obj("x")}, container=True)})

    result = await run_pipeline({"mod": [parent]}, [FakeParser()], _ctx(store))

    assert result == {"mod": GroupResult(created=2, existing=0, errors=0, unparsed=0)}
    assert "unresolved" not in caplog.text


class _UnreachableStore(MockNodeStore):
    async def existing_ids(self, ids: Collection[str]) -> set[str]:
        raise NodeStoreError("backend unreachable")


async def test_store_failure_during_discovery_counts_as_errors() -> None:
    store = _UnreachableStore()
    seeds = {"one": [Obj("a", {"c": Obj("child")})], "two": [Obj("b")]}

    result = await run_pipeline(seeds, [FakeParser()], _ctx(store))

    assert store.uploaded == []
    assert result == {
        "one": GroupResult(created=0, existing=0, errors=1, unparsed=0),
        "two": GroupResult(created=0, existing=0, errors=1, unparsed=0),
    }


class _ReadCountingStore(MockNodeStore):
    """Answers existence checks without ``read_node``; counts the reads."""

    def __init__(self) -> None:
        super().__init__()
        self.reads: Counter[str] = Counter()

    async def existing_ids(self, ids: Collection[str]) -> set[str]:
        self.existing_ids_calls.append(set(ids))
        return {i for i in ids if await super().read_node(i) is not None}

    async def read_node(self, node_id: str) -> NodeResponse | None:
        self.reads[node_id] += 1
        return await super().read_node(node_id)


async def test_stored_child_is_read_once_for_all_parents() -> None:
    store = _ReadCountingStore()
    old = Obj("old")
    _stored(store, old)
    seeds = [Obj(f"p{i}", {"c": old}) for i in range(3)]
    parser = FakeParser()

    await run_pipeline({"mod": seeds}, [parser], _ctx(store))

    assert store.reads[old.node_id] == 1
    assert all(parser.seen_children[f"p{i}"]["c"].name == "old" for i in range(3))


async def test_workflow_enrichment_describes_children_from_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Mapping[str, ResolvedChild] | None] = []

    # Mirrors generate_workflow_docstring's signature, hence its argument count.
    async def fake_generate_workflow_docstring(  # noqa: PLR0913
        ctx: ParseContext,
        name: str,
        source_code: str,
        docstring: str,
        wf_definition: Any,
        children_by_id: Mapping[str, ResolvedChild] | None = None,
    ) -> str:
        calls.append(children_by_id)
        return "Run the workflow.\n\nIt calls its child."

    monkeypatch.setattr(
        pipeline, "generate_workflow_docstring", fake_generate_workflow_docstring
    )
    store = MockNodeStore()
    child = Obj("child")
    parser = FakeParser(Enrichment.WORKFLOW)

    await run_pipeline({"mod": [Obj("wf", {"c": child})]}, [parser], _ctx(store))

    assert [{k: v.name for k, v in (c or {}).items()} for c in calls] == [
        {},  # the child itself has no children
        {child.node_id: "child"},
    ]
    (stored_wf,) = (n for n in store.uploaded if n.name == "wf")
    assert stored_wf.brief_description == "Run the workflow."


class ResultParser(FakeParser):
    """A container ``run`` carries one execution result for its ``target``."""

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        description = super().describe(obj, identity, children)
        if obj.source == "run":
            description.execution_results = [
                ExecutionResultRequest(
                    author_name="a",
                    author_email="a@example.com",
                    artifact_id=children["target"].id,
                    inputs=[],
                    outputs="42",
                )
            ]
        return description


async def test_container_stores_execution_results_for_its_children() -> None:
    store = MockNodeStore()
    target = Obj("target")
    run = Obj("run", {"target": target}, container=True)

    result = await run_pipeline({"mod": [run]}, [ResultParser()], _ctx(store))

    assert [r.artifact_id for r in store.uploaded_execution_results] == [target.node_id]
    assert result == {"mod": GroupResult(created=1, existing=0, errors=0, unparsed=0)}


class SourceObjParser(FakeParser):
    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        description = super().describe(obj, identity, children)
        if description.node is not None:
            description.node.source_obj = obj
        return description


async def test_source_obj_is_self_contained_after_enrichment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contained: list[Any] = []

    def fake_self_contain_source(
        settings: ToolkitSettings, obj: Any, source_code: str
    ) -> str:
        contained.append(obj)
        return f"# self-contained\n{source_code}"

    monkeypatch.setattr(pipeline, "self_contain_source", fake_self_contain_source)
    store = MockNodeStore()
    a = Obj("a")

    await run_pipeline({"mod": [a]}, [SourceObjParser()], _ctx(store))

    assert contained == [a]
    assert [n.source_code for n in store.uploaded] == ["# self-contained\na"]
