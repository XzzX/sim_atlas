from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.catalog import Catalog
from sim_atlas.dependencies import get_catalog
from sim_atlas.models import (
    FilterOptions,
    ScoredSearchResponse,
    SearchRequest,
    Suggestion,
    SuggestRequest,
)

router = APIRouter()


@router.get("/filter_options", response_model=FilterOptions, tags=["search"])
async def get_filter_options(
    catalog: Annotated[Catalog, Depends(get_catalog)],
):
    return catalog.get_filter_options()


@router.post(
    "/search",
    response_model=ScoredSearchResponse,
    tags=["search"],
    operation_id="search_nodes",
)
async def search_nodes(
    request: SearchRequest,
    catalog: Annotated[Catalog, Depends(get_catalog)],
):
    """Search the node catalog.

    Performs hybrid (semantic + keyword) search when embeddings are configured
    and falls back to keyword-only otherwise. Set ``semantic=false`` to force
    keyword-only search even when AI is available.
    """
    if request.semantic is False:
        return catalog.search(
            request.query, request.filter, page=request.page, limit=request.limit
        )
    return await catalog.search_hybrid(
        request.query, request.filter, page=request.page, limit=request.limit
    )


@router.post("/suggest", response_model=list[Suggestion], tags=["search"])
async def suggest_nodes(
    request: SuggestRequest,
    catalog: Annotated[Catalog, Depends(get_catalog)],
):
    """Fast type-ahead lookup: matches only the node name and import path.

    For the search-as-you-type list under the search box, not the results
    table — no docstrings, no semantic ranking, no `used_by`/connections
    enrichment. Honours the same filters as `/search` so the two stay in
    the same scope; not exposed as an MCP tool (ADR-0020).
    """
    return catalog.suggest(request.query, request.filter, limit=request.limit)
