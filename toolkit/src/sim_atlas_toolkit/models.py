from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, TypeAdapter


class ArtifactType(StrEnum):
    FUNCTION = "function"
    WORKFLOW = "workflow"


class Annotation(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None


class PackageRef(BaseModel):
    """How to install the distribution a node was parsed from.

    Records what an uploader's environment actually contained, not registry
    truth: the absence of a conda entry does not mean the package is
    unavailable on conda-forge (see ADR-0012 and ADR-0019).
    """

    ecosystem: Literal["pypi", "conda"]
    name: str
    version: str | None = None
    channel: str | None = None


class Reference(BaseModel):
    label: str
    id: str
    count: int


# --- Workflow internal-structure models ---
#
# A node is either a plain Python function or a workflow; the two differ only
# in that a workflow additionally records its internal dataflow graph
# (``uses``/``wf_definition``) — see ADR-0021. ``WfDefinition`` describes that
# graph and is shared by both request/response variants below.


class WfInputNode(BaseModel):
    type: Literal["input"] = "input"
    node_id: str
    outputs: list[Annotation]


class WfOutputNode(BaseModel):
    type: Literal["output"] = "output"
    node_id: str
    inputs: list[Annotation]


class WfFunctionNode(BaseModel):
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
    source_node: str
    source_port: str | None = None
    target_node: str
    target_port: str | None = None


class WfDefinition(BaseModel):
    nodes: list[WfNode]
    edges: list[WfEdge]


class NodeRequest(BaseModel):
    artifact_type: ArtifactType

    id: str | None = None
    hash: str | None = None
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
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    uses: list[Reference] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


class NodeResponse(BaseModel):
    artifact_type: ArtifactType

    id: str
    hash: str
    name: str
    category: str
    keywords: list[str]

    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

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
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    uses: list[Reference] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


node_request_adapter: TypeAdapter[NodeRequest] = TypeAdapter(NodeRequest)

node_response_adapter: TypeAdapter[NodeResponse] = TypeAdapter(NodeResponse)


class IOValue(BaseModel):
    label: str
    value: str | int | float | bool


class ExecutionResultRequest(BaseModel):
    author_name: str
    author_email: str

    artifact_id: str
    inputs: list[IOValue]
    outputs: str


class ExecutionResultResponse(BaseModel):
    id: str

    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    artifact_id: str
    inputs: list[IOValue]
    outputs: str
