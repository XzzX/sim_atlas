from fastmcp import FastMCP

from sim_atlas.dependencies import get_storage
from sim_atlas.models import ScoredSearchItem

mcp = FastMCP("Simulation Atlas")


@mcp.tool
async def search(query: str) -> list[ScoredSearchItem]:
    """Search the simulation node catalog and return the top 3 matches.

    Performs hybrid (semantic + keyword) search when embeddings are configured
    and falls back to keyword-only otherwise.
    """
    storage = get_storage()
    response = await storage.search_hybrid(query, None, page=1, limit=3)
    return response.results.data


mcp_app = mcp.http_app(path="/")
