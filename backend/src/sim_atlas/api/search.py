from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sim_atlas.dependencies import get_storage
from sim_atlas.models import (
    FilterOptions,
    ScoredSearchResponse,
    SearchRequest,
    Suggestion,
    SuggestRequest,
)
from sim_atlas.storage.storage_interface import StorageInterface

router = APIRouter()


@router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options(
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    return storage.get_filter_options()


@router.post(
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

    ``mode`` picks the ranking: ``hybrid`` (the default) fuses substring,
    keyword and — when embeddings are configured — semantic ranking;
    ``keyword``, ``substring`` and ``semantic`` run one leg alone.
    ``semantic`` needs a query and an embedding provider. Without ``mode``,
    ``semantic=false`` still forces keyword-only search.
    """
    mode = request.mode or ("keyword" if request.semantic is False else "hybrid")
    query, filter, page, limit = (
        request.query,
        request.filter,
        request.page,
        request.limit,
    )
    match mode:
        case "keyword":
            return storage.search(query, filter, page=page, limit=limit)
        case "substring":
            return storage.search_substring(query, filter, page=page, limit=limit)
        case "semantic":
            if not query or not query.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="semantic search needs a query",
                )
            return await storage.search_semantic(query, filter, page=page, limit=limit)
        case "hybrid":
            return await storage.search_hybrid(query, filter, page=page, limit=limit)


@router.post("/suggest", response_model=list[Suggestion], tags=["search"])
async def suggest_nodes(
    request: SuggestRequest,
    storage: Annotated[StorageInterface, Depends(get_storage)],
):
    """Fast type-ahead lookup: matches only the node name and import path.

    For the search-as-you-type list under the search box, not the results
    table — no docstrings, no semantic ranking, no `used_by`/connections
    enrichment. Honours the same filters as `/search` so the two stay in
    the same scope; not exposed as an MCP tool (ADR-0020).
    """
    return storage.suggest(request.query, request.filter, limit=request.limit)
