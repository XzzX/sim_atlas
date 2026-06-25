import datetime as dt
import hashlib
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from sim_atlas.agent import run_agent_stream
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.models import (
    AgentRequest,
    ArtifactRequest,
    ArtifactResponse,
    Filter,
    FilterOptions,
    FunctionMetadata,
    FunctionRequest,
    ScoredSearchResponse,
    StoredArtifact,
    WorkflowMetadata,
    WorkflowRequest,
)
from sim_atlas.security import Creator, get_current_user
from sim_atlas.settings import load_settings
from sim_atlas.storage_interface import (
    ArtifactAlreadyExistsError,
    ArtifactDuplicateError,
    StorageInterface,
    get_storage_backend,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage = get_storage_backend()
    yield
    app.state.storage = None


def get_storage(request: Request) -> StorageInterface:
    storage: StorageInterface | None = getattr(request.app.state, "storage", None)
    assert storage is not None, "Storage has not been initialised"
    return storage


app = FastAPI(
    lifespan=lifespan,
    title="Simulation Atlas",
    description="One place to store all your simulation knowledge. Upload your functions, search for existing ones, and let AI enrich your documentation.",
    version="0.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AINotConfiguredError)
async def ai_not_configured_handler(
    request: Request, exc: AINotConfiguredError
) -> Response:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI features are not configured",
    )


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


def compose_artifact(request: ArtifactRequest, creator: Creator) -> StoredArtifact:
    match request:
        case FunctionRequest():
            return FunctionMetadata(
                id=str(uuid.uuid4()),
                author_name=request.author_name,
                author_email=request.author_email,
                creator_name=creator.name,
                creator_email=creator.email,
                creation_timestamp=dt.datetime.now(dt.UTC).isoformat(),
                name=request.name,
                artifact_type=request.artifact_type,
                category=request.category,
                keywords=request.keywords,
                homepage_url=request.homepage_url,
                documentation_url=request.documentation_url,
                source_url=request.source_url,
                python_import=request.python_import,
                dependencies=request.dependencies,
                source_code=request.source_code,
                docstring=request.docstring,
                brief_description=request.brief_description or "",
                description=request.description or "",
                hash=hashlib.sha256(request.source_code.encode()).hexdigest(),
                inputs=request.inputs,
                outputs=request.outputs,
            )
        case WorkflowRequest():
            return WorkflowMetadata(
                id=str(uuid.uuid4()),
                author_name=request.author_name,
                author_email=request.author_email,
                creator_name=creator.name,
                creator_email=creator.email,
                creation_timestamp=dt.datetime.now(dt.UTC).isoformat(),
                name=request.name,
                artifact_type=request.artifact_type,
                category=request.category,
                keywords=request.keywords,
                homepage_url=request.homepage_url,
                documentation_url=request.documentation_url,
                source_url=request.source_url,
                source_code=request.source_code,
                docstring=request.docstring,
                brief_description=request.brief_description or "",
                description=request.description or "",
                inputs=request.inputs,
                outputs=request.outputs,
                see_also=request.see_also,
                children=request.children,
                wf_definition=request.wf_definition,
                hash=hashlib.sha256(request.source_code.encode()).hexdigest(),
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact type",
            )


@api_router.post("/artifacts", tags=["artifacts"], status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: ArtifactRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> dict[str, str]:
    artifact = compose_artifact(request, creator)

    try:
        return {"id": storage.create(artifact)}
    except ArtifactAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"id": e.id, "message": "Artifact with the same id already exists."},
        ) from e
    except ArtifactDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "id": e.id,
                "message": "Artifact with the same hash already exists.",
            },
        ) from e


@api_router.get("/artifacts/{artifact_id}", tags=["artifacts"])
async def read_artifact(
    artifact_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ArtifactResponse:
    try:
        return storage.read(artifact_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e


@api_router.put("/artifacts/{artifact_id}", tags=["artifacts"])
async def update_artifact(
    artifact_id: str,
    request: ArtifactRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ArtifactResponse:
    artifact = compose_artifact(request, creator)

    try:
        result = storage.update(artifact_id, artifact)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e

    return result


@api_router.delete("/artifacts/{artifact_id}", tags=["artifacts"])
async def delete_artifact(
    artifact_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    try:
        storage.delete(artifact_id)
        return {"detail": "Artifact deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e


@api_router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options(
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    return storage.get_filter_options()


@api_router.post("/search", response_model=ScoredSearchResponse, tags=["search"])
async def search_nodes(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    query: str | None = None,
    filter_options: Filter | None = None,
    page: int = 1,
    limit: int = 10,
):
    return storage.search(query, filter_options, page=page, limit=limit)


@api_router.post(
    "/semantic_search",
    response_model=ScoredSearchResponse,
    tags=["search"],
    operation_id="semantic_search",
)
async def semantic_search(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    query: str,
    filter_options: Filter | None = None,
    page: int = 1,
    limit: int = 10,
):
    return await storage.search_hybrid(query, filter_options, page=page, limit=limit)


@api_router.post(
    "/hybrid_search",
    response_model=ScoredSearchResponse,
    tags=["search"],
    operation_id="hybrid_search",
)
async def hybrid_search(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    query: str,
    filter_options: Filter | None = None,
    page: int = 1,
    limit: int = 10,
):
    return await storage.search_hybrid(query, filter_options, page=page, limit=limit)


@api_router.post(
    "/enrich",
    tags=["ai"],
)
async def enrich(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
    only_ids: list[str] | None = None,
) -> None:
    await storage.enrich(only_ids=only_ids)


@api_router.post(
    "/agent/stream",
    tags=["ai"],
    operation_id="agent_stream",
    response_class=StreamingResponse,
)
async def agent_stream(
    request: AgentRequest,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> StreamingResponse:
    settings = load_settings()
    if (
        not settings.llm_api_key
        or not settings.llm_base_url
        or not settings.llm_chat_model
    ):
        raise AINotConfiguredError
    return StreamingResponse(
        run_agent_stream(request, storage),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


app.include_router(api_router)


@app.get("/ide")
async def redirect_to_ide():
    return RedirectResponse(url="/ide/")


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/ide", StaticFiles(directory=STATIC_DIR / "ide", html=True), name="ide")

# Create an MCP server based on this app
mcp = FastApiMCP(
    app,
    name="My API MCP",
    description="Very cool MCP server",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=["semantic_search", "hybrid_search", "agent"],
)

# Mount the MCP server directly to your app
mcp.mount_http()

app.mount(
    "/", StaticFiles(directory=STATIC_DIR / "frontend", html=True), name="frontend"
)
