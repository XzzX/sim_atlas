from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.security import Creator, get_current_user
from sim_atlas.settings import load_settings

router = APIRouter()


@router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


@router.get("/capabilities", tags=["meta"])
async def get_capabilities() -> dict[str, bool]:
    settings = load_settings()
    return {
        "agent_enabled": settings.agent_enabled,
        "embeddings_enabled": settings.embeddings_enabled,
    }
