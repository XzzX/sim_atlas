import datetime as dt
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from .ai import enrich_metadata_with_ai
from .models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeRequest,
    NodeResponse,
    ScoredSearchResponse,
)
from .storage import get_storage_backend

# Get the configured storage backend
storage = get_storage_backend()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup and shutdown events"""
    storage.connect()
    try:
        yield
    finally:
        storage.close()


app = FastAPI(
    title="Simulation Atlas",
    description="One place to store all your simulation knowledge. Upload your functions, search for existing ones, and let AI enrich your documentation.",
    version="0.0.0",
    lifespan=lifespan,
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


@api_router.get("/nodes/{node_hash}", tags=["nodes"])
async def read_node(node_hash: str) -> NodeResponse:
    node = storage.get(node_hash, None)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )
    return node


@api_router.post("/nodes", tags=["nodes"])
async def create_node(node: NodeRequest) -> NodeResponse:
    if node.source_code_hash in storage:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Node already exists"
        )

    timestamp = dt.datetime.now(dt.UTC)
    node_metadata = NodeMetadata(
        **node.model_dump(),
        ai_docstring="",
        creator_name="Sebastian",
        creator_email="asdf@asdf.de",
        creation_timestamp=timestamp.isoformat(),
    )

    try:
        storage[node_metadata.source_code_hash] = node_metadata
        return node_metadata
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@api_router.put("/nodes/{node_hash}", tags=["nodes"])
async def update_node(node_hash: str, node: NodeMetadata) -> NodeResponse:
    if node_hash not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
        )
    storage[node_hash] = node
    return node


@api_router.delete("/nodes/{node_hash}", tags=["nodes"])
async def delete_node(node_hash: str):
    if node_hash not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="node not found"
        )
    del storage[node_hash]
    return {"detail": "Node deleted"}


@api_router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options():
    return storage.get_filter_options()


@api_router.post("/search", response_model=list[ScoredSearchResponse], tags=["search"])
async def search_nodes(query: str | None = None, filter_options: Filter | None = None):
    query = query.strip() if query else ""
    filter_options = filter_options or Filter()
    return storage.search(query, filter_options)


@api_router.post(
    "/semantic_search",
    response_model=list[ScoredSearchResponse],
    tags=["search"],
    operation_id="semantic_search",
)
async def semantic_search(query: str):
    return storage.search_semantic(query, 10)


@api_router.post(
    "/enrich",
    tags=["ai"],
)
async def enrich_node(node_hash: str) -> NodeResponse:
    node = storage.get(node_hash, None)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found"
        )

    node = enrich_metadata_with_ai(node)
    storage[node_hash] = node

    return node


app.include_router(api_router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

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
