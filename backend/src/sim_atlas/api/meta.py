from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.dependencies import get_storage
from sim_atlas.security import Creator, get_current_user
from sim_atlas.storage.storage_interface import StorageInterface

router = APIRouter()


@router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


@router.get("/capabilities", tags=["meta"])
async def get_capabilities(
    storage: Annotated[StorageInterface, Depends(get_storage)],
) -> dict[str, bool]:
    return {"embeddings_enabled": storage.embeddings_enabled}
