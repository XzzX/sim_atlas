"""The wire schema shared by the sim-atlas backend and toolkit (ADR-0024).

Field ownership is enforced by types:

* Request models (``extra="forbid"``) contain only client-owned fields, so a
  client cannot send, and the server never trusts, a server-owned value.
* Response models (``extra="ignore"``) add the server-generated and
  server-derived fields and ignore unknown top-level fields. Client-owned
  models nested in a response (``WfDefinition`` and its nodes and edges,
  ``PackageRef``, ``IOValue``, ``Annotation``) keep ``extra="forbid"``, so a
  new field there needs the lockstep release on both sides.

Shared fields are defined once in private ``_…Fields`` base classes, generic
over the annotation and reference types where the two sides differ.
"""

from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Discriminator

_REQUEST = ConfigDict(extra="forbid")
_RESPONSE = ConfigDict(extra="ignore")


class ArtifactType(StrEnum):
    FUNCTION = "function"
    WORKFLOW = "workflow"


class PackageRef(BaseModel):
    """How to install the distribution a node was parsed from.

    Records what an uploader's environment actually contained, not registry
    truth: the absence of a conda entry does not mean the package is
    unavailable on conda-forge (see ADR-0012 and ADR-0019).
    """

    model_config = _REQUEST

    ecosystem: Literal["pypi", "conda"]
    name: str
    version: str | None = None
    channel: str | None = None


# --- References between nodes ---


class _ReferenceFields(BaseModel):
    label: str
    id: str
    count: int


class Reference(_ReferenceFields):
    """A client-sent reference to another node (``uses``, ``see_also``)."""

    model_config = _REQUEST


class ReferenceResponse(_ReferenceFields):
    """A reference as the server returns it.

    ``artifact_type`` is derived by the server from the referenced node; it is
    ``None`` when that node is not in the catalog.
    """

    model_config = _RESPONSE

    artifact_type: ArtifactType | None = None


# --- Port annotations ---


class _AnnotationFields(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None


class Annotation(_AnnotationFields):
    """A client-sent port annotation."""

    model_config = _REQUEST


class AnnotationResponse(_AnnotationFields):
    """A port annotation as the server returns it.

    ``connections`` (other nodes wired to this port) is derived by the server.
    """

    model_config = _RESPONSE

    connections: list[ReferenceResponse] | None = None


# --- Workflow internal-structure models ---
#
# A node is either a plain Python function or a workflow; the two differ only
# in that a workflow additionally records its internal dataflow graph
# (``uses``/``wf_definition``) — see ADR-0021. ``WfDefinition`` describes that
# graph. It is client-owned in both directions, so its ports are ``Annotation``
# even inside ``NodeResponse``.


class WfInputNode(BaseModel):
    model_config = _REQUEST

    type: Literal["input"] = "input"
    node_id: str
    outputs: list[Annotation]


class WfOutputNode(BaseModel):
    model_config = _REQUEST

    type: Literal["output"] = "output"
    node_id: str
    inputs: list[Annotation]


class WfFunctionNode(BaseModel):
    model_config = _REQUEST

    type: Literal["function"] = "function"
    node_id: str
    inputs: list[Annotation]
    outputs: list[Annotation]
    atlas_id: str | None


WfNode = Annotated[
    WfInputNode | WfOutputNode | WfFunctionNode,
    Discriminator("type"),
]


class WfEdge(BaseModel):
    model_config = _REQUEST

    source_node: str
    source_port: str | None = None
    target_node: str
    target_port: str | None = None


class WfDefinition(BaseModel):
    model_config = _REQUEST

    nodes: list[WfNode]
    edges: list[WfEdge]


# --- Nodes ---

AnnT = TypeVar("AnnT", bound=_AnnotationFields)
RefT = TypeVar("RefT", bound=_ReferenceFields)


class _NodeFields(BaseModel, Generic[AnnT, RefT]):
    """Every client-owned node field, once."""

    artifact_type: ArtifactType

    name: str
    category: str
    keywords: list[str]

    author_name: str = "unknown"
    author_email: str = "unknown"

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    python_import: str | None = None
    dependencies: list[str] | None = None
    packages: list[PackageRef] = []

    source_code: str

    docstring: str | None = None
    brief_description: str | None = None
    description: str | None = None
    inputs: list[AnnT]
    outputs: list[AnnT]

    see_also: list[RefT] = []
    uses: list[RefT] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


class NodeRequest(_NodeFields[Annotation, Reference]):
    """A node upload, function or workflow alike (ADR-0021).

    ``id`` and ``hash`` are client-owned; the server defaults both to
    ``sha256(source_code)`` when they are omitted (ADR-0005).
    """

    model_config = _REQUEST

    id: str | None = None
    hash: str | None = None


class NodeResponse(_NodeFields[AnnotationResponse, ReferenceResponse]):
    """A stored node with its server-generated and server-derived fields."""

    model_config = _RESPONSE

    id: str
    hash: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    used_by: list[ReferenceResponse] | None = None


# --- Execution results ---


class IOValue(BaseModel):
    model_config = _REQUEST

    label: str
    value: str | int | float | bool


class _ExecutionResultFields(BaseModel):
    author_name: str
    author_email: str

    artifact_id: str
    inputs: list[IOValue]
    outputs: str


class ExecutionResultRequest(_ExecutionResultFields):
    model_config = _REQUEST


class ExecutionResultResponse(_ExecutionResultFields):
    model_config = _RESPONSE

    id: str

    creator_name: str
    creator_email: str
    creation_timestamp: str
