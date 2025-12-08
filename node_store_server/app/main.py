from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from node_store_spec.models import (
    NodeFilter,
    NodeIndex,
    NodeRequest,
    SemanticSearchResponse,
)

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


@app.get("/node-index/", response_model=list[NodeIndex])
async def read_node_index():
    return [
        NodeIndex(
            module=item.module,
            qualname=item.qualname,
            source_code_hash=item.source_code_hash,
        )
        for item in storage.list()
        if item.module and item.qualname
    ]


@app.post("/nodes/", response_model=str)
async def create_node(node: NodeRequest):
    """Create a new node metadata entry"""

    if storage.exists(node.source_code_hash):
        raise HTTPException(status_code=401, detail="Node already exists")

    node_metadata = NodeMetadata(**node.model_dump(), ai_docstring="")

    try:
        return storage.create(node_metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/nodes/list", response_model=list[NodeResponse])
async def read_nodes(filter: NodeFilter | None = None):
    """Retrieve all node metadata entries"""
    return storage.list(filter)


@app.get("/nodes/{node_hash}", response_model=NodeResponse)
async def read_node(node_hash: str):
    """Retrieve a specific node metadata entry by its hash"""
    node = storage.read(node_hash)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@app.put("/nodes/{node_hash}", response_model=NodeResponse)
async def update_node(node_hash: str, node: NodeMetadata):
    """Update an existing node metadata entry"""
    success = storage.update(node_hash, node)
    if not success:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@app.delete("/nodes/{node_hash}")
async def delete_node(node_hash: str):
    """Delete a node metadata entry"""
    success = storage.delete(node_hash)
    if not success:
        raise HTTPException(status_code=404, detail="node not found")
    return {"detail": "Node deleted"}


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
