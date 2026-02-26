import datetime as dt
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from .html import render_node_detail_page, render_search_page
from .models import (
    NodeMetadata,
    NodeRequest,
    NodeResponse,
    NodeType,
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
    title="Node Store",
    description="A metadata storage system for nodes",
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


@app.get("/", include_in_schema=False)
async def root(query: str | None = None) -> HTMLResponse:
    """Root endpoint - Search interface"""

    nodes = storage.search(query) if query else storage.filter()
    search_page = render_search_page(query or "", nodes)

    return HTMLResponse(content=search_page)


app.mount("/ide", StaticFiles(directory="ide", html=True), name="ide")


@app.get("/nodes-detail/{node_hash}", include_in_schema=False)
async def read_node_html(node_hash: str) -> HTMLResponse:
    """Get detailed HTML view of a node"""
    print("node_hash", node_hash)
    node = storage.get(node_hash, None)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return HTMLResponse(content=render_node_detail_page(node))


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/nodes", tags=["nodes"], response_model=list[NodeResponse])
async def list_nodes(qualname: str | None = None, type: NodeType | None = None):
    return storage.filter(qualname, type)


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


@api_router.post("/search", response_model=list[ScoredSearchResponse], tags=["search"])
async def search_nodes(query: str):
    """
    Search for nodes matching the given criteria.

    Request body should be a dictionary with field-value pairs:
    {"author": "John Doe", "email": "john@example.com"}
    """
    return storage.search(query)


@api_router.post(
    "/semantic_search",
    response_model=list[ScoredSearchResponse],
    tags=["search"],
    operation_id="semantic_search",
)
async def semantic_search(query: str):
    """
    Perform semantic search on node metadata.

    Args:
        query: Natural language search query
        limit: Maximum number of results (default: 10)
    """
    return storage.search_semantic(query, 10)


app.include_router(api_router)

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
