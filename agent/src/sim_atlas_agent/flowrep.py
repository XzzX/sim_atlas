from flowrep.prospective.workflow_recipe import WorkflowRecipe

import httpx
from sim_atlas_agent.tools.wf import Graph
from sim_atlas_agent.models.sim_atlas import WorkflowResponse


async def read_artifact(
    api_url: str,
    artifact_id: str,
) -> WorkflowResponse:
    return httpx.get(
        f"{api_url}/artifacts/{artifact_id}",
    )

def graph_to_flowrep(g: Graph) -> WorkflowRecipe:

