from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


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

    author_name: str = "Unknown"
    author_email: str = "Unknown"

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
