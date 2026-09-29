from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.catalog import Catalog
from sim_atlas.dependencies import get_catalog
from sim_atlas.security import Creator, get_current_user

router = APIRouter()


@router.post(
    "/enrich",
    tags=["ai"],
)
async def enrich(
    catalog: Annotated[Catalog, Depends(get_catalog)],
    _: Annotated[Creator, Depends(get_current_user)],
    only_ids: list[str] | None = None,
) -> None:
    await catalog.enrich(only_ids=only_ids)


@router.post(
    "/embed",
    tags=["ai"],
)
async def embed(
    catalog: Annotated[Catalog, Depends(get_catalog)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    await catalog.embed_missing()
