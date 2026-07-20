from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

STATIC_DIR = Path(__file__).parent / "static"


async def _redirect_to_ide(request: Request) -> RedirectResponse:
    query = request.url.query
    return RedirectResponse(url="/ide/?" + query if query else "/ide/")


async def _spa_fallback(
    request: Request, exc: StarletteHTTPException
) -> Response | FileResponse:
    is_frontend_route = (
        exc.status_code == status.HTTP_404_NOT_FOUND
        and request.method == "GET"
        and not request.url.path.startswith("/api/")
        and not request.url.path.startswith("/ide")
        and not request.url.path.startswith("/mcp")
    )
    if is_frontend_route:
        return FileResponse(STATIC_DIR / "frontend" / "index.html")
    return await http_exception_handler(request, exc)


def mount_spas(app: FastAPI) -> None:
    """Wire up the built SPA assets: /ide, the frontend catch-all, and the SPA
    fallback handler.

    Call this last during app assembly — the frontend mount at ``/`` is a
    catch-all and must come after every other route and mount.
    """
    app.get("/ide")(_redirect_to_ide)

    # The built SPAs are gitignored and only produced at build time, so these
    # dirs can be absent in a dev/CI checkout. Ensure they exist so mounting
    # doesn't raise at import; a missing asset then just 404s.
    for sub in ("frontend", "ide"):
        (STATIC_DIR / sub).mkdir(parents=True, exist_ok=True)

    app.mount("/ide", StaticFiles(directory=STATIC_DIR / "ide", html=True), name="ide")

    app.exception_handler(StarletteHTTPException)(_spa_fallback)

    app.mount(
        "/",
        StaticFiles(directory=STATIC_DIR / "frontend", html=True),
        name="frontend",
    )
