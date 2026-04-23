import datetime as dt
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from sim_atlas_backend.models import (
    AgentRequest,
    AgentResponse,
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeRequest,
    NodeResponse,
    ScoredSearchResponse,
)

from .agent import run_agent

from .security import Creator, get_current_user
from .storage_interface import StorageInterface, get_storage_backend


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage = get_storage_backend()
    yield


def get_storage(request: Request) -> StorageInterface:
    return request.app.state.storage


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

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/items")
async def get_items(storage: Annotated[StorageInterface, Depends(get_storage)]):
    storage.count()  # Example of accessing the storage backend from the app state
    return {"message": "Hello, World!"}


@api_router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


@api_router.post("/nodes", tags=["nodes"], status_code=status.HTTP_201_CREATED)
async def create_node(
    node: NodeRequest,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> str:
    value = node.source_code if node.source_code else node.name
    id = hashlib.sha256(value.encode()).hexdigest()

    timestamp = dt.datetime.now(dt.UTC)
    node_metadata = NodeMetadata(
        **node.model_dump(),
        id=id,
        ai_docstring="",
        creator_name=creator.name,
        creator_email=creator.email,
        creation_timestamp=timestamp.isoformat(),
    )

    try:
        return storage.create(node_metadata)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Node already exists"
        ) from e


@api_router.get("/nodes/{node_id}", tags=["nodes"])
async def read_node(
    node_id: str, storage: Annotated[StorageInterface, Depends(get_storage)]
) -> NodeResponse:
    try:
        return storage.read(node_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        ) from e


@api_router.put("/nodes/{node_id}", tags=["nodes"])
async def update_node(
    node_id: str,
    node: NodeMetadata,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> NodeResponse:
    try:
        return storage.update(node_id, node)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
        ) from e


@api_router.delete("/nodes/{node_id}", tags=["nodes"])
async def delete_node(
    node_id: str,
    creator: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    try:
        storage.delete(node_id)
        return {"detail": "Node deleted"}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
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
    return storage.search_semantic(query, filter_options, page=page, limit=limit)


@api_router.post(
    "/enrich",
    tags=["ai"],
)
async def enrich(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    storage.enrich()


@api_router.post(
    "/agent",
    response_model=AgentResponse,
    tags=["ai"],
    operation_id="agent",
)
async def agent(
    request: AgentRequest,
    _: Annotated[Creator, Depends(get_current_user)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> AgentResponse:
    return run_agent(request, storage)


app.include_router(api_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/ide", StaticFiles(directory=STATIC_DIR / "ide", html=True), name="ide")
app.mount(
    "/", StaticFiles(directory=STATIC_DIR / "frontend", html=True), name="frontend"
)

# Create an MCP server based on this app
mcp = FastApiMCP(
    app,
    name="My API MCP",
    description="Very cool MCP server",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=["semantic_search", "agent"],
)

# Mount the MCP server directly to your app
mcp.mount_http()
