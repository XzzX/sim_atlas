import base64
import gzip
from enum import StrEnum
from typing import Annotated, Any, Literal

import numpy as np
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    PlainSerializer,
    Tag,
    model_validator,
)


def nd_array_custom_before_validator(x: np.ndarray | dict[str, str]) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    raw = gzip.decompress(base64.b64decode(x["data"]))
    return np.frombuffer(raw, dtype=np.dtype(x["dtype"]))


def nd_array_custom_serializer(x: np.ndarray) -> dict[str, str]:
    data = {
        "dtype": str(x.dtype),
        "data": base64.b64encode(gzip.compress(x.tobytes())).decode("utf-8"),
    }

    return data


NdArray = Annotated[
    np.ndarray,
    BeforeValidator(nd_array_custom_before_validator),
    PlainSerializer(nd_array_custom_serializer, return_type=dict[str, str]),
]


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


class FunctionRequest(BaseModel):
    artifact_type: Literal[ArtifactType.FUNCTION] = ArtifactType.FUNCTION

    name: str
    category: str
    keywords: list[str]

    author_name: str
    author_email: str

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    brief_description: str | None = None
    description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]


class FunctionResponse(BaseModel):
    artifact_type: Literal[ArtifactType.FUNCTION] = ArtifactType.FUNCTION

    id: str
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

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    brief_description: str | None = None
    description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]


class FunctionMetadata(FunctionResponse):
    embedding: NdArray | None = None
    hash: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


# --- Workflow models ---


class WfInputNode(BaseModel):
    id: str
    type: Literal["input"] = "input"
    name: str
    default: Any = None


class WfOutputNode(BaseModel):
    id: str
    type: Literal["output"] = "output"
    name: str


class WfFunctionNode(BaseModel):
    id: str
    type: Literal["function"] = "function"
    python_import: str
    atlas_node_id: str | None = None


class WfPackNode(BaseModel):
    id: str
    type: Literal["pack"] = "pack"
    python_import: str
    atlas_node_id: str | None = None


class WfUnpackNode(BaseModel):
    id: str
    type: Literal["unpack"] = "unpack"
    python_import: str
    atlas_node_id: str | None = None


WfNode = Annotated[
    WfInputNode | WfOutputNode | WfFunctionNode | WfPackNode | WfUnpackNode,
    Discriminator("type"),
]


class WfEdge(BaseModel):
    source: str
    source_port: str | None = None
    target: str
    target_port: str | None = None


class WorkflowDefinition(BaseModel):
    nodes: list[WfNode]
    edges: list[WfEdge]


class WorkflowRequest(BaseModel):
    author_name: str = "unknown"
    author_email: str = "unknown"

    name: str
    artifact_type: Literal[ArtifactType.WORKFLOW] = ArtifactType.WORKFLOW
    category: str
    keywords: list[str]

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    brief_description: str | None = None
    description: str | None = None

    inputs: list[Annotation]
    outputs: list[Annotation]

    definition: WorkflowDefinition

    @model_validator(mode="after")
    def check_io_names_match_definition(self) -> "WorkflowRequest":
        input_names = {
            n.name for n in self.definition.nodes if isinstance(n, WfInputNode)
        }
        output_names = {
            n.name for n in self.definition.nodes if isinstance(n, WfOutputNode)
        }
        request_input_labels = {a.label for a in self.inputs if a.label is not None}
        request_output_labels = {a.label for a in self.outputs if a.label is not None}
        if request_input_labels != input_names:
            raise ValueError(
                f"inputs annotation labels {request_input_labels} do not match "
                f"WfInputNode names {input_names}"
            )
        if request_output_labels != output_names:
            raise ValueError(
                f"outputs annotation labels {request_output_labels} do not match "
                f"WfOutputNode names {output_names}"
            )
        return self


class WorkflowResponse(BaseModel):
    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    id: str
    name: str
    artifact_type: Literal[ArtifactType.WORKFLOW] = ArtifactType.WORKFLOW
    category: str
    keywords: list[str]

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    brief_description: str | None = None
    description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]

    definition: WorkflowDefinition


class WorkflowMetadata(WorkflowResponse):
    embedding: NdArray | None = None
    hash: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


StoredArtifact = Annotated[
    Annotated[FunctionMetadata, Tag("function")]
    | Annotated[WorkflowMetadata, Tag("workflow")],
    Discriminator("artifact_type"),
]

ArtifactRequest = Annotated[
    Annotated[FunctionRequest, Tag("function")]
    | Annotated[WorkflowRequest, Tag("workflow")],
    Discriminator("artifact_type"),
]

ArtifactResponse = Annotated[
    Annotated[FunctionResponse, Tag("function")]
    | Annotated[WorkflowResponse, Tag("workflow")],
    Discriminator("artifact_type"),
]


class Filter(BaseModel):
    category: str | None = None
    artifact_type: list[ArtifactType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None
    datatypes: list[str] | None = None
    units: list[str] | None = None
    quantities: list[str] | None = None
    port_type: Literal["inputs", "outputs", "both"] | None = None


class FilterOptions(BaseModel):
    category: dict[str, list[str]]
    artifact_type: list[ArtifactType]
    author: list[str]
    keywords: list[str]
    datatypes: list[str]
    units: list[str]
    quantities: list[str]


class ScoredSearchItem(BaseModel):
    score: float
    node: FunctionResponse | WorkflowResponse


class SearchResults(BaseModel):
    data: list[ScoredSearchItem]
    page: int
    limit: int
    total_items: int
    total_pages: int


class ScoredSearchResponse(BaseModel):
    results: SearchResults
    aggregations: dict[str, dict[str, int]] | None = None


# --- Agent models ---


class GraphNodeContext(BaseModel):
    """Compact representation of a node already placed in the graph."""

    graph_id: str
    node_kind: Literal["function", "input", "output"]
    atlas_node_id: str | None = None  # None for InputNode / OutputNode
    name: str
    short_description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]


class GraphEdgeContext(BaseModel):
    source_graph_id: str
    source_handle: str
    target_graph_id: str
    target_handle: str


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    query: str
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    history: list[HistoryMessage] = []
    session_id: str | None = None
    user_id: str = "default"


class AgentResponse(BaseModel):
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    message: str
