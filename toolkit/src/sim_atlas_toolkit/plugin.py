"""The two-phase parser contract (ADR-0025).

A parser turns one Python object into nodes in two synchronous, pure steps:
``identify`` (cheap: which nodes would this object yield, and which objects
does it reference) and ``describe`` (the full node requests, given the
already-resolved children). All I/O — existence checks, LLM enrichment,
storing — lives in ``sim_atlas_toolkit.pipeline``.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from sim_atlas_models import (
    Annotation,
    AnnotationResponse,
    ArtifactType,
    ExecutionResultRequest,
    NodeRequest,
    NodeResponse,
)


@dataclass(frozen=True, slots=True)
class Identity:
    """What ``identify`` knows about an object before describing it."""

    node_ids: tuple[str, ...]
    """Content hashes (= ids) of the nodes this object yields; ``()`` marks a
    container that yields no node of its own."""

    children: Mapping[str, Any] = field(default_factory=dict[str, Any])
    """Label -> object referenced by this one; processed before it."""

    data: Any = None
    """Parser-private, handed back to ``describe`` to avoid recomputation."""


@dataclass(frozen=True, slots=True)
class ResolvedChild:
    """What a parent may know about a child node."""

    id: str
    artifact_type: ArtifactType
    name: str
    docstring: str | None
    brief_description: str | None
    description: str | None
    inputs: list[Annotation]
    outputs: list[Annotation]

    @classmethod
    def from_response(cls, node: NodeResponse) -> "ResolvedChild":
        """Build from a stored node, dropping the server-derived port fields."""

        def ports(anns: list[AnnotationResponse]) -> list[Annotation]:
            return [
                Annotation.model_validate(a.model_dump(exclude={"connections"}))
                for a in anns
            ]

        return cls(
            id=node.id,
            artifact_type=node.artifact_type,
            name=node.name,
            docstring=node.docstring,
            brief_description=node.brief_description,
            description=node.description,
            inputs=ports(node.inputs),
            outputs=ports(node.outputs),
        )


class Enrichment(StrEnum):
    """Which enrichment the pipeline runs on a draft before storing it."""

    FUNCTION = "function"
    """``generate_docstring`` + ``enrich_from_docstring``."""
    WORKFLOW = "workflow"
    """``generate_workflow_docstring`` + ``enrich_from_docstring``."""
    NONE = "none"


@dataclass(slots=True)
class NodeDraft:
    """A node as ``describe`` produced it, before enrichment and validation."""

    request: NodeRequest
    """May be built with ``model_construct``; the pipeline validates it."""

    enrichment: Enrichment

    source_obj: Any | None = None
    """If set, ``self_contain_source(settings, source_obj, source)`` runs
    after enrichment."""


@dataclass(slots=True)
class Description:
    """Everything ``describe`` produced for one object."""

    nodes: list[NodeDraft]
    execution_results: list[ExecutionResultRequest] = field(
        default_factory=list[ExecutionResultRequest]
    )


class Parser(Protocol):
    """A two-phase parser. Both methods are synchronous and pure: no store,
    no settings, no network."""

    name: str

    def identify(self, obj: Any) -> Identity | None:
        """Return ``None`` if *obj* is not this parser's.

        Must be cheap: no LLM, no griffe, no I/O beyond imports.
        """
        ...

    def describe(
        self, obj: Any, identity: Identity, children: Mapping[str, ResolvedChild]
    ) -> Description:
        """Describe *obj*. ``children`` holds only the labels that resolved;
        a missing label must be tolerated (omit the reference)."""
        ...
