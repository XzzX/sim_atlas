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

    source_code: str
    docstring: str | None = None

    brief_description: str | None = None
    description: str | None = None

    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    children: list[Reference] = []


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

    source_code: str
    docstring: str | None = None

    brief_description: str | None = None
    description: str | None = None
    inputs: list[Annotation]
    outputs: list[Annotation]

    see_also: list[Reference] = []
    children: list[Reference] = []


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

artifact_response_adapter: TypeAdapter[FunctionResponse | WorkflowResponse] = TypeAdapter(
    ArtifactResponse
)
