from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.dependencies import get_storage
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage.storage_interface import StorageInterface

router = APIRouter()


@router.post(
    "/embed",
    tags=["ai"],
)
async def embed(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    await storage.embed_missing()
