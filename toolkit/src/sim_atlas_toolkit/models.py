from enum import StrEnum

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
    author_name: str = "unknown"
    author_email: str = "unknown"

    name: str
    artifact_type: str = "function"
    category: str
    keywords: list[str]

    homepage_url: str = ""
    documentation_url: str = ""
    source_url: str = ""

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class FunctionResponse(BaseModel):
    author_name: str
    author_email: str

    creator_name: str
    creator_email: str
    creation_timestamp: str

    id: str
    name: str
    artifact_type: str
    category: str
    keywords: list[str]

    homepage_url: str
    documentation_url: str
    source_url: str

    python_import: str
    dependencies: list[str] | None = None

    source_code: str

    docstring: str
    ai_summary: str
    ai_description: str
    inputs: list[Annotation]
    outputs: list[Annotation]


class ScoredSearchItem(BaseModel):
    score: float
    node: FunctionResponse


class SearchResults(BaseModel):
    data: list[ScoredSearchItem]
    page: int
    limit: int
    total_items: int
    total_pages: int


class ScoredSearchResponse(BaseModel):
    results: SearchResults
    aggregations: dict[str, dict[str, int]] | None = None


class FunctionMetadata(FunctionResponse):
    embedding: list[float] | None = None


class Filter(BaseModel):
    category: str | None = None
    artifact_type: list[ArtifactType] | None = None
    author: list[str] | None = None
    keywords: list[str] | None = None
    datatypes: list[str] | None = None
    units: list[str] | None = None
    quantities: list[str] | None = None


class FilterOptions(BaseModel):
    category: dict[str, list[str]]
    artifact_type: list[ArtifactType]
    author: list[str]
    keywords: list[str]
    datatypes: list[str]
    units: list[str]
    quantities: list[str]
