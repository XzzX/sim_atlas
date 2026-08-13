from typing import Annotated

from fastapi import APIRouter, Depends

from sim_atlas.llm_providers import LLM_REASONING_EFFORTS
from sim_atlas.models import CapabilitiesResponse, LLMProviderInfo
from sim_atlas.security import Creator, get_current_user
from sim_atlas.settings import load_settings

router = APIRouter()


@router.get("/me")
async def return_creator(
    creator: Annotated[Creator, Depends(get_current_user)],
) -> Creator:
    return creator


@router.get("/capabilities", tags=["meta"])
async def get_capabilities() -> CapabilitiesResponse:
    settings = load_settings()
    return CapabilitiesResponse(
        embeddings_enabled=settings.embeddings_enabled,
        # The operator's allowlist of endpoints a caller may point the agent at.
        # The server's own llm_base_url / llm_chat_model are deliberately absent:
        # they drive docstring enrichment only, so publishing them here would
        # just mislead about where an agent request goes.
        llm_providers=[
            LLMProviderInfo.from_provider(p) for p in settings.llm_providers
        ],
        llm_default_provider=settings.llm_default_provider,
        llm_reasoning_efforts=list(LLM_REASONING_EFFORTS),
    )
