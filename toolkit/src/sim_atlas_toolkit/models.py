from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Tag, TypeAdapter


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


class Reference(BaseModel):
    label: str
    id: str


class FunctionRequest(BaseModel):
    artifact_type: Literal[ArtifactType.FUNCTION] = ArtifactType.FUNCTION

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
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []


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

    see_also: list[Reference] = []


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

    python_import: str | None = None
    dependencies: list[str] | None = None

    source_code: str
    docstring: str | None = None
    brief_description: str | None = None
    description: str | None = None

    inputs: list[Annotation]
    outputs: list[Annotation]

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
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    uses: list[Reference] = []

    wf_definition: WfDefinition = WfDefinition(nodes=[], edges=[])


ArtifactRequest = Annotated[
    Annotated[FunctionRequest, Tag("function")]
    | Annotated[WorkflowRequest, Tag("workflow")],
    Discriminator("artifact_type"),
]

artifact_request_adapter: TypeAdapter[FunctionRequest | WorkflowRequest] = TypeAdapter(
    ArtifactRequest
)

ArtifactResponse = Annotated[
    Annotated[FunctionResponse, Tag("function")]
    | Annotated[WorkflowResponse, Tag("workflow")],
    Discriminator("artifact_type"),
]

artifact_response_adapter: TypeAdapter[FunctionResponse | WorkflowResponse] = (
    TypeAdapter(ArtifactResponse)
)


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
