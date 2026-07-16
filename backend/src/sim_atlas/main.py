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
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from starlette.exceptions import HTTPException as StarletteHTTPException

from sim_atlas.agent import run_agent_stream
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.models import (
    AgentRequest,
    AnnotationResponse,
    ArtifactRequest,
    ArtifactResponse,
    ExecutionResultMetadata,
    ExecutionResultRequest,
    ExecutionResultResponse,
    FilterOptions,
    FunctionMetadata,
    FunctionRequest,
    ScoredSearchResponse,
    SearchRequest,
    StoredArtifact,
    WorkflowMetadata,
    WorkflowRequest,
)
from sim_atlas.security import Creator, get_current_user
from sim_atlas.settings import load_settings
from sim_atlas.storage_interface import (
    ArtifactAlreadyExistsError,
    ArtifactDuplicateError,
    ExecutionResultAlreadyExistsError,
    ExecutionResultDuplicateError,
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
                id=request.id
                or hashlib.sha256(request.source_code.encode()).hexdigest(),
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
                hash=request.hash
                or hashlib.sha256(request.source_code.encode()).hexdigest(),
                inputs=[AnnotationResponse(**a.model_dump()) for a in request.inputs],
                outputs=[AnnotationResponse(**a.model_dump()) for a in request.outputs],
                see_also=request.see_also,
            )
        case WorkflowRequest():
            return WorkflowMetadata(
                id=request.id or str(uuid.uuid4()),
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
                inputs=[AnnotationResponse(**a.model_dump()) for a in request.inputs],
                outputs=[AnnotationResponse(**a.model_dump()) for a in request.outputs],
                see_also=request.see_also,
                uses=request.uses,
                wf_definition=request.wf_definition,
                hash=request.hash
                or hashlib.sha256(request.source_code.encode()).hexdigest(),
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid artifact type",
            )


@api_router.post("/artifacts", tags=["artifacts"], status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: ArtifactRequest,
    response: Response,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ArtifactResponse:
    artifact = compose_artifact(request, creator)

    try:
        response.status_code = status.HTTP_201_CREATED
        return storage.create_artifact(artifact)
    except ArtifactAlreadyExistsError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.artifact
    except ArtifactDuplicateError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.artifact


@api_router.get("/artifacts/{artifact_id}", tags=["artifacts"])
async def read_artifact(
    artifact_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ArtifactResponse:
    try:
        return storage.read_artifact(artifact_id)
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
        result = storage.update_artifact(artifact_id, artifact)
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
        storage.delete_artifact(artifact_id)
        return {"detail": "Artifact deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Artifact not found"},
        ) from e


def compose_execution_result(
    request: ExecutionResultRequest, creator: Creator
) -> ExecutionResultMetadata:
    hash_input = (
        request.artifact_id
        + "".join(f"{v.label}={v.value}" for v in request.inputs)
        + request.outputs
    )
    return ExecutionResultMetadata(
        id=str(uuid.uuid4()),
        author_name=request.author_name,
        author_email=request.author_email,
        creator_name=creator.name,
        creator_email=creator.email,
        creation_timestamp=dt.datetime.now(dt.UTC).isoformat(),
        artifact_id=request.artifact_id,
        inputs=request.inputs,
        outputs=request.outputs,
        hash=hashlib.sha256(hash_input.encode()).hexdigest(),
    )


@api_router.post(
    "/execution_results",
    tags=["execution_results"],
    status_code=status.HTTP_201_CREATED,
)
async def create_execution_result(
    request: ExecutionResultRequest,
    response: Response,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    result = compose_execution_result(request, creator)
    try:
        response.status_code = status.HTTP_201_CREATED
        return storage.create_execution_result(result)
    except ExecutionResultAlreadyExistsError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.execution_result
    except ExecutionResultDuplicateError as e:
        response.status_code = status.HTTP_409_CONFLICT
        return e.execution_result


@api_router.get(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def read_execution_result(
    result_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    try:
        return storage.read_execution_result(result_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@api_router.put(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def update_execution_result(
    result_id: str,
    request: ExecutionResultRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> ExecutionResultResponse:
    result = compose_execution_result(request, creator)
    try:
        return storage.update_execution_result(result_id, result)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@api_router.delete(
    "/execution_results/{result_id}",
    tags=["execution_results"],
)
async def delete_execution_result(
    result_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> dict[str, str]:
    try:
        storage.delete_execution_result(result_id)
        return {"detail": "Execution result deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"id": e.args[0], "message": "Execution result not found"},
        ) from e


@api_router.get(
    "/artifacts/{artifact_id}/execution_results",
    tags=["execution_results"],
)
async def list_execution_results_by_artifact(
    artifact_id: str,
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> list[ExecutionResultMetadata]:
    return storage.read_execution_results_by_artifact(artifact_id)


@api_router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options(
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    return storage.get_filter_options()


@api_router.post(
    "/search",
    response_model=ScoredSearchResponse,
    tags=["search"],
    operation_id="search_nodes",
)
async def search_nodes(
    request: SearchRequest,
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    """Search the node catalog.

    Performs hybrid (semantic + keyword) search when embeddings are configured
    and falls back to keyword-only otherwise. Set ``semantic=false`` to force
    keyword-only search even when AI is available.
    """
    if request.semantic is False:
        return storage.search(
            request.query, request.filter, page=request.page, limit=request.limit
        )
    return await storage.search_hybrid(
        request.query, request.filter, page=request.page, limit=request.limit
    )


@api_router.get("/capabilities", tags=["meta"])
async def get_capabilities() -> dict[str, bool]:
    settings = load_settings()
    return {
        "agent_enabled": settings.agent_enabled,
        "embeddings_enabled": settings.embeddings_enabled,
    }


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
    "/embed",
    tags=["ai"],
)
async def embed(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    await storage.embed_missing()


if load_settings().agent_enabled:

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
async def redirect_to_ide(request: Request) -> RedirectResponse:
    query = request.url.query
    return RedirectResponse(url="/ide/?" + query if query else "/ide/")


STATIC_DIR = Path(__file__).parent / "static"

# The built SPAs are gitignored and only produced at build time, so these dirs
# can be absent in a dev/CI checkout. Ensure they exist so mounting doesn't
# raise at import; a missing asset then just 404s.
for sub in ("frontend", "ide"):
    (STATIC_DIR / sub).mkdir(parents=True, exist_ok=True)

app.mount("/ide", StaticFiles(directory=STATIC_DIR / "ide", html=True), name="ide")


@app.exception_handler(StarletteHTTPException)
async def spa_fallback(
    request: Request, exc: StarletteHTTPException
) -> Response | FileResponse:
    is_frontend_route = (
        exc.status_code == status.HTTP_404_NOT_FOUND
        and request.method == "GET"
        and not request.url.path.startswith("/api/")
        and not request.url.path.startswith("/ide")
    )
    if is_frontend_route:
        return FileResponse(STATIC_DIR / "frontend" / "index.html")
    return await http_exception_handler(request, exc)


# Create an MCP server based on this app
mcp = FastApiMCP(
    app,
    name="My API MCP",
    description="Very cool MCP server",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=["search_nodes", "agent"],
)

# Mount the MCP server directly to your app
mcp.mount_http()

app.mount(
    "/", StaticFiles(directory=STATIC_DIR / "frontend", html=True), name="frontend"
)
