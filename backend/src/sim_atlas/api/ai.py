from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from sim_atlas.agent import run_agent_stream
from sim_atlas.dependencies import get_storage
from sim_atlas.models import AgentRequest
from sim_atlas.security import Creator, get_current_user
from sim_atlas.settings import load_settings
from sim_atlas.storage_interface import StorageInterface

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
    await storage.enrich(only_ids=only_ids)


@router.post(
    "/embed",
    tags=["ai"],
)
async def embed(
    storage: Annotated[StorageInterface, Depends(get_storage)],
    _: Annotated[Creator, Depends(get_current_user)],
) -> None:
    await storage.embed_missing()


if load_settings().agent_enabled:

    @router.post(
        "/agent/stream",
        tags=["ai"],
        operation_id="agent_stream",
        response_class=StreamingResponse,
    )
    async def agent_stream(
        request: AgentRequest,
        storage: Annotated[StorageInterface, Depends(get_storage)],
    ) -> StreamingResponse:
        return StreamingResponse(
            run_agent_stream(request, storage),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
