from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from sim_atlas.api import api_router
from sim_atlas.dependencies import set_storage
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.mcp_server import mcp, mcp_app
from sim_atlas.static_files import mount_spas
from sim_atlas.storage_interface import get_storage_backend

# `mcp` is re-exported here (in addition to `app`) because tests import it from
# `sim_atlas.main`; `__all__` marks it as an intentional re-export.
__all__ = ["app", "mcp"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_storage(get_storage_backend())
    async with mcp_app.lifespan(app):
        yield
    set_storage(None)


app = FastAPI(
    lifespan=lifespan,
    title="Simulation Atlas",
    description="One place to store all your simulation knowledge. Upload your functions, search for existing ones, and let AI enrich your documentation.",
    version="0.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AINotConfiguredError)
async def ai_not_configured_handler(
    request: Request, exc: AINotConfiguredError
) -> Response:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI features are not configured",
    )


app.include_router(api_router)

app.mount("/mcp", mcp_app)

mount_spas(app)
