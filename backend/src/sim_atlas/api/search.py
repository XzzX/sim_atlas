from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.dependencies import get_storage
from sim_atlas.models import (
    FilterOptions,
    ScoredSearchResponse,
    SearchRequest,
)
from sim_atlas.storage_interface import StorageInterface

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
