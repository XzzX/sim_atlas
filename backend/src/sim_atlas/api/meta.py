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
async def get_capabilities() -> dict[str, bool | str | None]:
    settings = load_settings()
    return {
        # True when the server alone can run the agent, i.e. the caller needs to
        # supply nothing. When it is False but both llm_base_url and
        # llm_chat_model are set, callers can still bring their own API key.
        "agent_enabled": settings.agent_enabled,
        "embeddings_enabled": settings.embeddings_enabled,
        "llm_base_url": settings.llm_base_url,
        "llm_chat_model": settings.llm_chat_model,
    }
