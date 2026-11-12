"""Worklist pipeline driving two-phase parsers (ADR-0025).

1. Discover level by level: identify every new object, check the store once
   per level for which ids exist, and expand only the children of entries
   that are missing.
2. Build children first: describe, enrich, validate and store each missing
   entry once all its children are finished; independent entries run
   concurrently.
3. Count every node, children included, in the group of the first seed that
   reached it.
"""

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from sim_atlas_models import NodeRequest, NodeResponse

from sim_atlas_toolkit.context import ParseContext
from sim_atlas_toolkit.node_store import NodeStatus, NodeStore, NodeStoreError
from sim_atlas_toolkit.parsers.ai_enrichment import (
    generate_docstring,
    generate_workflow_docstring,
)
from sim_atlas_toolkit.parsers.metadata import (
    enrich_from_docstring,
    self_contain_source,
)
from sim_atlas_toolkit.plugin import (
    Enrichment,
    Identity,
    NodeDraft,
    Parser,
    ResolvedChild,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GroupResult:
    """Per-group outcome of `run_pipeline`; counts nodes, children included."""

    created: int
    existing: int
    errors: int
    unparsed: int


@dataclass(slots=True)
class _Counts:
    created: int = 0
    existing: int = 0
    errors: int = 0
    unparsed: int = 0


@dataclass(eq=False, slots=True)
class _Entry:
    """One identified object (or several objects with identical node ids)."""

    obj: Any
    parser: Parser
    identity: Identity
    group: str
    children: dict[str, "_Entry | None"] = field(
        default_factory=dict[str, "_Entry | None"]
    )
    """Label -> child entry; ``None`` when the child could not be identified."""
    missing: bool = True
    failed: bool = False
    stored: list[NodeResponse] = field(default_factory=list[NodeResponse])
    done: asyncio.Event = field(default_factory=asyncio.Event)


class _ChildOf(NamedTuple):
    """The parent entry and the label it references an object by."""

    parent: _Entry
    label: str


@dataclass(frozen=True, slots=True)
class _Reached:
    """An object reached from a seed list or from a parent's children."""

    obj: Any
    group: str
    via: _ChildOf | None = None


async def run_pipeline(
    seeds: Mapping[str, Sequence[Any]],
    parsers: Sequence[Parser],
    ctx: ParseContext,
    concurrency: int = 10,
) -> dict[str, GroupResult]:
    """Identify, describe and store *seeds* and everything they reference.

    *seeds* maps a group label (module name) to its collected objects;
    *parsers* are asked in order and the first non-``None`` identity wins.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    counts = {group: _Counts() for group in seeds}
    missing = await _discover(seeds, parsers, ctx.store, counts)
    for entry in _cyclic(missing):
        logger.error("%r is part of a reference cycle", entry.obj)
        _fail(entry, counts[entry.group])

    semaphore = asyncio.Semaphore(concurrency)

    async def build(entry: _Entry) -> None:
        try:
            for child in entry.children.values():
                if child is not None and child.missing:
                    await child.done.wait()
            async with semaphore:
                await _build(entry, ctx, counts[entry.group])
        except Exception:
            logger.exception("Failed to parse %r", entry.obj)
            _fail(entry, counts[entry.group])
        finally:
            entry.done.set()

    await asyncio.gather(*(build(e) for e in missing if not e.done.is_set()))

    for group, c in counts.items():
        logger.info(
            "Upload summary for %s: %d created, %d existing, %d errors, %d unparsed",
            group,
            c.created,
            c.existing,
            c.errors,
            c.unparsed,
        )
    return {
        group: GroupResult(c.created, c.existing, c.errors, c.unparsed)
        for group, c in counts.items()
    }


async def _discover(
    seeds: Mapping[str, Sequence[Any]],
    parsers: Sequence[Parser],
    store: NodeStore,
    counts: dict[str, _Counts],
) -> list[_Entry]:
    """Identify everything reachable through missing entries; return those."""
    by_obj: dict[int, _Entry | None] = {}
    by_ids: dict[tuple[str, ...], _Entry] = {}
    # ``by_obj`` is keyed by ``id(obj)``: keep every object alive for the run
    # so an id is never reused by a different object.
    keep_alive: list[Any] = []
    missing: list[_Entry] = []

    frontier: list[_Reached] = [
        _Reached(obj, group) for group, objs in seeds.items() for obj in objs
    ]
    while frontier:
        level: list[_Entry] = []
        for reached in frontier:
            key = id(reached.obj)
            if key in by_obj:
                entry = by_obj[key]
            else:
                keep_alive.append(reached.obj)
                entry = _identify(reached, parsers, counts[reached.group])
                if entry is not None and entry.identity.node_ids:
                    if (same := by_ids.get(entry.identity.node_ids)) is not None:
                        entry = same
                    else:
                        by_ids[entry.identity.node_ids] = entry
                        level.append(entry)
                elif entry is not None:
                    level.append(entry)
                by_obj[key] = entry
            if reached.via is not None:
                reached.via.parent.children[reached.via.label] = entry

        frontier = []
        ids = {i for entry in level for i in entry.identity.node_ids}
        try:
            existing = await store.existing_ids(ids) if ids else set[str]()
        except NodeStoreError:
            logger.exception("Failed to check which of %d nodes exist", len(ids))
            for entry in level:
                _fail(entry, counts[entry.group])
            continue
        for entry in level:
            node_ids = entry.identity.node_ids
            entry.missing = not node_ids or not existing.issuperset(node_ids)
            if not entry.missing:
                counts[entry.group].existing += len(node_ids)
                entry.done.set()
                continue
            missing.append(entry)
            frontier.extend(
                _Reached(child, entry.group, _ChildOf(entry, label))
                for label, child in entry.identity.children.items()
            )
    return missing


def _identify(
    reached: _Reached, parsers: Sequence[Parser], counts: _Counts
) -> _Entry | None:
    where = (
        ""
        if reached.via is None
        else f" (child {reached.via.label!r} of {reached.via.parent.obj!r})"
    )
    for parser in parsers:
        try:
            identity = parser.identify(reached.obj)
        except Exception:
            logger.exception(
                "%s failed to identify %r%s", parser.name, reached.obj, where
            )
            counts.errors += 1
            return None
        if identity is not None:
            return _Entry(reached.obj, parser, identity, reached.group)
    logger.warning("No parser available for %r%s", reached.obj, where)
    counts.unparsed += 1
    return None


def _cyclic(entries: list[_Entry]) -> list[_Entry]:
    """Entries on a reference cycle among *entries* (missing ones only)."""
    visiting: set[int] = set()
    finished: set[int] = set()
    on_cycle: dict[int, _Entry] = {}
    stack: list[_Entry] = []

    def visit(entry: _Entry) -> None:
        visiting.add(id(entry))
        stack.append(entry)
        for child in entry.children.values():
            if child is None or not child.missing or id(child) in finished:
                continue
            if id(child) in visiting:
                for member in stack[stack.index(child) :]:
                    on_cycle[id(member)] = member
            else:
                visit(child)
        stack.pop()
        visiting.discard(id(entry))
        finished.add(id(entry))

    for entry in entries:
        if id(entry) not in finished:
            visit(entry)
    return list(on_cycle.values())


def _fail(entry: _Entry, counts: _Counts) -> None:
    """Mark *entry* failed and count an error for each node it would yield."""
    entry.failed = True
    counts.errors += max(1, len(entry.identity.node_ids))
    entry.done.set()


async def _build(entry: _Entry, ctx: ParseContext, counts: _Counts) -> None:
    children: dict[str, ResolvedChild] = {}
    for label, child in entry.children.items():
        # An unidentified child (``None``) was already reported in discovery.
        if child is not None and child.failed:
            logger.warning(
                "Child %r of %r failed; describing without it", label, entry.obj
            )
        elif child is not None and (resolved := await _resolve(child, ctx.store)):
            children[label] = resolved

    description = entry.parser.describe(entry.obj, entry.identity, children)
    described = [d.request.id for d in description.nodes]
    if described != list(entry.identity.node_ids):
        raise ValueError(
            f"{entry.parser.name}: described ids {described} differ from "
            f"identified ids {list(entry.identity.node_ids)}"
        )

    by_id = {child.id: child for child in children.values()}
    requests = [await _finish(draft, ctx, by_id) for draft in description.nodes]
    results = await ctx.store.create_nodes(requests) if requests else []
    for execution_result in description.execution_results:
        await ctx.store.create_execution_result(execution_result)

    entry.stored = [r.node for r in results]
    created = sum(r.status is NodeStatus.CREATED for r in results)
    counts.created += created
    counts.existing += len(results) - created


async def _resolve(child: _Entry, store: NodeStore) -> ResolvedChild | None:
    """What a parent may know about finished *child*.

    ``None`` unless the child is exactly one node: a container has none, and
    the children mapping has no room for several.
    """
    if len(child.identity.node_ids) != 1:
        return None
    if child.missing:
        (node,) = child.stored
    elif (node := await store.read_node(child.identity.node_ids[0])) is None:
        logger.warning("Stored node %s vanished", child.identity.node_ids[0])
        return None
    return ResolvedChild.from_response(node)


async def _finish(
    draft: NodeDraft, ctx: ParseContext, children: Mapping[str, ResolvedChild]
) -> NodeRequest:
    """Enrich *draft* and validate it into a sendable request."""
    request = draft.request
    match draft.enrichment:
        case Enrichment.FUNCTION:
            request.docstring = await generate_docstring(
                ctx, request.source_code, request.docstring or ""
            )
            enrich_from_docstring(request.docstring, request)
        case Enrichment.WORKFLOW:
            request.docstring = await generate_workflow_docstring(
                ctx,
                request.name,
                request.source_code,
                request.docstring or "",
                request.wf_definition,
                children=children,
            )
            enrich_from_docstring(request.docstring, request)
        case Enrichment.NONE:
            pass
    if draft.source_obj is not None:
        request.source_code = self_contain_source(
            ctx.settings, draft.source_obj, request.source_code
        )
    # serialize_as_any: dump nested values by their runtime type, so a
    # response-side value (e.g. ``AnnotationResponse.connections``) reaches
    # validation and is rejected instead of being silently dropped.
    return NodeRequest.model_validate(request.model_dump(serialize_as_any=True))
