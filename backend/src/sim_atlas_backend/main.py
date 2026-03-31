import datetime as dt
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from sim_atlas_backend.ai import enrich_metadata_with_ai
from sim_atlas_backend.models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeRequest,
    NodeResponse,
    ScoredSearchResponse,
)

from .ai import create_ai_docstring
from .security import Creator, get_current_user
from .storage_interface import get_storage_backend
from .voyage_ai import create_embedding

# Get the configured storage backend
storage = get_storage_backend()

app = FastAPI(
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


@api_router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


@api_router.get("/nodes/{node_hash}", tags=["nodes"])
async def read_node(node_hash: str) -> NodeResponse:
    node = storage.get(node_hash, None)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )
    return node


@api_router.post("/nodes", tags=["nodes"], status_code=status.HTTP_201_CREATED)
async def create_node(
    node: NodeRequest, creator: Annotated[Creator, Depends(get_current_user)]
) -> NodeResponse:
    if node.source_code_hash in storage:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Node already exists"
        )

    timestamp = dt.datetime.now(dt.UTC)
    node_metadata = NodeMetadata(
        **node.model_dump(),
        ai_docstring="",
        creator_name=creator.name,
        creator_email=creator.email,
        creation_timestamp=timestamp.isoformat(),
    )

    try:
        storage[node_metadata.source_code_hash] = node_metadata
        return node_metadata
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@api_router.put("/nodes/{node_hash}", tags=["nodes"])
async def update_node(
    node_hash: str,
    node: NodeMetadata,
    creator: Annotated[Creator, Depends(get_current_user)],
) -> NodeResponse:
    if node_hash not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
        )
    storage[node_hash] = node
    return node


@api_router.delete("/nodes/{node_hash}", tags=["nodes"])
async def delete_node(
    node_hash: str, creator: Annotated[Creator, Depends(get_current_user)]
):
    if node_hash not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
        )
    del storage[node_hash]
    return {"detail": "Node deleted"}


@api_router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options():
    return storage.get_filter_options()


@api_router.post("/search", response_model=ScoredSearchResponse, tags=["search"])
async def search_nodes(
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
async def enrich(_: Annotated[Creator, Depends(get_current_user)]) -> None:
    storage.enrich()


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
    include_operations=["semantic_search"],
)

# Mount the MCP server directly to your app
mcp.mount_http()
