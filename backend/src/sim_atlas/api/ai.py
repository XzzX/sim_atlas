from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas import discovery
from sim_atlas.dependencies import get_storage
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage.storage_interface import StorageInterface

router = APIRouter()


@router.post(
    "/enrich",
    tags=["ai"],
)
async def enrich(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
    only_ids: list[str] | None = None,
) -> None:
    await discovery.enrich(storage, only_ids=only_ids)


@router.post(
    "/embed",
    tags=["ai"],
)
async def embed(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    await discovery.embed_missing(storage)
