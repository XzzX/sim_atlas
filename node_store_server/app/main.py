from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from node_store_spec.models import (
    NodeFilter,
    NodeRequest,
    SemanticSearchResponse,
)

from app.security import has_read_access

from .models import (
    NodeMetadata,
    NodeResponse,
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Node Store!", "status": "running"}


@app.post("/nodes/")
async def create_node(node: NodeRequest) -> NodeResponse:
    if node.source_code_hash in storage:
        raise HTTPException(status_code=401, detail="Node already exists")

    node_metadata = NodeMetadata(**node.model_dump(), ai_docstring="")

    try:
        storage[node_metadata.source_code_hash] = node_metadata
        return node_metadata
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/nodes/{node_hash}")
async def read_node(node_hash: str) -> NodeResponse:
    node = storage.get(node_hash, None)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.put("/nodes/{node_hash}")
async def update_node(node_hash: str, node: NodeMetadata) -> NodeResponse:
    if node_hash not in storage:
        raise HTTPException(status_code=404, detail="node not found")
    storage[node_hash] = node
    return node


@app.delete("/nodes/{node_hash}")
async def delete_node(node_hash: str):
    if node_hash not in storage:
        raise HTTPException(status_code=404, detail="node not found")
    del storage[node_hash]
    return {"detail": "Node deleted"}


@app.get("/node-index/")
async def read_node_index() -> list[str]:
    return [item.python_import for item in storage.values() if item.python_import]


@app.post("/nodes/list")
async def read_nodes(
    key: Annotated[str, Depends(has_read_access)], filter: NodeFilter | None = None
) -> list[NodeResponse]:
    return [NodeResponse(**x.model_dump()) for x in storage.filter(filter)]


@app.post("/nodes/search", response_model=list[NodeResponse])
async def search_nodes(query: str):
    """
    Search for nodes matching the given criteria.

    Request body should be a dictionary with field-value pairs:
    {"author": "John Doe", "email": "john@example.com"}
    """
    return storage.search(query)


@app.post(
    "/nodes/semantic_search",
    response_model=list[SemanticSearchResponse],
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
