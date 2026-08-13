import base64
import gzip
from enum import StrEnum
from typing import Annotated, Literal

import numpy as np
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    PlainSerializer,
    Tag,
)

from sim_atlas.llm_providers import LLMProvider, ReasoningEffort


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


class Reference(BaseModel):
    label: str
    id: str
    count: int
    artifact_type: ArtifactType | None = None


class AnnotationRequest(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None


class AnnotationResponse(BaseModel):
    has_default_value: bool = False
    label: str | None = None
    datatype: str | None = None
    unit: str | None = None
    quantity: str | None = None
    description: str | None = None
    connections: list[Reference] | None = None


class FunctionRequest(BaseModel):
    artifact_type: Literal[ArtifactType.FUNCTION] = ArtifactType.FUNCTION

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

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    brief_description: str | None = None
    description: str | None = None
    inputs: list[AnnotationRequest]
    outputs: list[AnnotationRequest]

    see_also: list[Reference] = []


class FunctionResponse(BaseModel):
    artifact_type: Literal[ArtifactType.FUNCTION] = ArtifactType.FUNCTION

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

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    brief_description: str | None = None
    description: str | None = None
    inputs: list[AnnotationResponse]
    outputs: list[AnnotationResponse]

    see_also: list[Reference] = []
    used_by: list[Reference] | None = None


class FunctionMetadata(FunctionResponse):
    embedding: NdArray | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# --- Workflow models ---


class WfInputNode(BaseModel):
    type: Literal["input"] = "input"
    node_id: str
    outputs: list[AnnotationRequest]


class WfOutputNode(BaseModel):
    type: Literal["output"] = "output"
    node_id: str
    inputs: list[AnnotationRequest]


class WfFunctionNode(BaseModel):
    type: Literal["function"] = "function"
    node_id: str
    inputs: list[AnnotationRequest]
    outputs: list[AnnotationRequest]
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


class WorkflowRequest(BaseModel):
    author_name: str = "unknown"
    author_email: str = "unknown"

    id: str | None = None
    hash: str | None = None
    name: str
    artifact_type: Literal[ArtifactType.WORKFLOW] = ArtifactType.WORKFLOW
    category: str
    keywords: list[str]

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    python_import: str | None = None
    dependencies: list[str] | None = None

    source_code: str
    docstring: str | None = None
    brief_description: str | None = None
    description: str | None = None

    inputs: list[AnnotationRequest]
    outputs: list[AnnotationRequest]

    see_also: list[Reference] = []
    uses: list[Reference] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


class WorkflowResponse(BaseModel):
    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    id: str
    hash: str
    name: str
    artifact_type: Literal[ArtifactType.WORKFLOW] = ArtifactType.WORKFLOW
    category: str
    keywords: list[str]

    homepage_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None

    python_import: str | None = None
    dependencies: list[str] | None = None

    source_code: str
    docstring: str | None = None

    brief_description: str | None = None
    description: str | None = None
    inputs: list[AnnotationResponse]
    outputs: list[AnnotationResponse]

    see_also: list[Reference] = []
    uses: list[Reference] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


class WorkflowMetadata(WorkflowResponse):
    embedding: NdArray | None = None

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


class SearchRequest(BaseModel):
    query: str | None = None
    filter: Filter | None = None
    semantic: bool | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)


# --- Agent models ---


class GraphNodeContext(BaseModel):
    """Compact representation of a node already placed in the graph."""

    graph_id: str
    node_kind: Literal["function", "input", "output"]
    atlas_node_id: str | None = None  # None for InputNode / OutputNode
    name: str
    short_description: str | None = None
    inputs: list[AnnotationResponse]
    outputs: list[AnnotationResponse]


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
    # Caller-supplied credentials and selection, used for this request only and
    # never stored. `llm_provider` is an opaque id resolved against the operator's
    # allowlist (`settings.llm_providers`): the caller never supplies a URL, so
    # this endpoint cannot be pointed at an arbitrary host. `llm_chat_model` must
    # be one the selected provider offers. See ADR-0019.
    llm_api_key: str | None = None
    llm_provider: str | None = None
    llm_chat_model: str | None = None
    # Dropped rather than forwarded when the selected model does not accept it.
    llm_reasoning_effort: ReasoningEffort | None = None


class AgentResponse(BaseModel):
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    message: str


class LLMModelInfo(BaseModel):
    name: str
    label: str
    supports_reasoning_effort: bool


class LLMProviderInfo(BaseModel):
    """A provider as advertised to clients.

    `base_url` is published so a user can see where their key is being sent; it
    is informational only — clients select a provider by `id`.
    """

    id: str
    label: str
    base_url: str
    models: list[LLMModelInfo]
    default_model: str
    requires_api_key: bool

    @classmethod
    def from_provider(cls, provider: LLMProvider) -> "LLMProviderInfo":
        return cls(
            id=provider.id,
            label=provider.label,
            base_url=provider.base_url,
            models=[
                LLMModelInfo(
                    name=m.name,
                    label=m.display_label,
                    supports_reasoning_effort=m.reasoning_effort,
                )
                for m in provider.models
            ],
            default_model=provider.resolved_default_model.name,
            requires_api_key=provider.requires_api_key,
        )


class CapabilitiesResponse(BaseModel):
    embeddings_enabled: bool
    # Providers the agent may be pointed at. The agent always runs on a
    # caller-supplied key, so there is no "agent enabled" flag: an agent run is
    # possible whenever this list is non-empty and the user has a key.
    llm_providers: list[LLMProviderInfo]
    llm_default_provider: str | None
    llm_reasoning_efforts: list[str]


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


class ExecutionResultMetadata(ExecutionResultResponse):
    hash: str = ""
