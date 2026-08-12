from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from sim_atlas.agent import resolve_llm_config, run_agent_stream, with_keepalive
from sim_atlas.dependencies import get_storage
from sim_atlas.models import AgentRequest
from sim_atlas.security import Creator, get_current_user
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
    # Resolve before streaming starts: once the response headers are flushed the
    # AINotConfiguredError handler can no longer turn this into a 503.
    llm = resolve_llm_config(request)
    return StreamingResponse(
        with_keepalive(run_agent_stream(request, storage, llm)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
