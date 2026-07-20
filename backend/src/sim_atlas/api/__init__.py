from fastapi import APIRouter

from sim_atlas.api.ai import router as ai_router
from sim_atlas.api.artifacts import router as artifacts_router
from sim_atlas.api.execution_results import router as execution_results_router
from sim_atlas.api.meta import router as meta_router
from sim_atlas.api.search import router as search_router

api_router = APIRouter(prefix="/api/v1")
for _router in (
    artifacts_router,
    execution_results_router,
    search_router,
    meta_router,
    ai_router,
):
    api_router.include_router(_router)

__all__ = ["api_router"]
