import json

from langfuse.openai import AsyncOpenAI  # pyright: ignore[reportPrivateImportUsage]
from pydantic import BaseModel

from sim_atlas_backend.models import (
    FunctionMetadata,
    StoredArtifact,
    WfFunctionNode,
    WfPackNode,
    WfUnpackNode,
    WorkflowMetadata,
)
from sim_atlas_backend.storage_interface import StorageInterface

from .exceptions import AINotConfiguredError
from .settings import load_settings


def _strip_think_tags(raw: str) -> str:
    if "<think>" in raw and "</think>" in raw:
        start = raw.find("<think>")
        end = raw.find("</think>") + len("</think>")
        raw = raw[:start] + raw[end:]
    return raw.strip()


async def enrich_function_metadata(func: FunctionMetadata) -> None:
    settings = load_settings()
    if (
        not settings.llm_api_key
        or not settings.llm_base_url
        or not settings.llm_chat_model
    ):
        raise AINotConfiguredError(
            "LLM settings (llm_api_key, llm_api_url, llm_chat_model) are not configured"
        )
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    output_labels = [a.label for a in func.outputs if a.label]

    response = await client.chat.completions.create(
        model=settings.llm_chat_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": f"""You are a search-indexing assistant for a scientific simulation node catalog.
Given a Python function, produce search-optimized descriptions as a JSON object with exactly these keys:

"summary": One concise sentence (≤20 words) that names what the function does, what it takes as input and what it returns.
  - Use terminology a user would type into a search box.
  - Include the function name or a clear paraphrase of it.

"description": 2-5 sentences that expand on the summary for semantic search embedding.
  - Mention what the inputs represent and what the output represents in physical or conceptual terms (not just type names).
  - Use natural synonyms and alternative phrasings to maximize recall (e.g. both "velocity" and "speed").

"args": An object mapping each parameter name and return value name to a one-sentence description of its physical or conceptual meaning.
  - Use the exact parameter name as the key (e.g. "temperature", "return").
  - Describe what the value represents in domain terms, not just its type (e.g. "initial temperature of the simulation box in Kelvin").
  - Include all inputs and outputs; use "return" for a single return value or the tuple element name for multiple.

Return only the JSON object, no other text.

Here is the function to describe:
```python
{func.source_code}
```
The parsed output port names are (use these exact strings as keys for outputs in the args object): 
{", ".join(output_labels) if output_labels else ""}
""",
            }
        ],
    )

    raw = _strip_think_tags(response.choices[0].message.content or "{}")

    class _AIDescriptionResponse(BaseModel):
        summary: str
        description: str
        args: dict[str, str] = {}

    result = _AIDescriptionResponse.model_validate(json.loads(raw))
    func.brief_description = result.summary
    func.description = result.description
    for a in func.inputs + func.outputs:
        if a.label and a.description is None:
            a.description = result.args.get(a.label)


async def enrich_workflow_metadata(
    workflow: WorkflowMetadata, storage: StorageInterface
) -> None:

    def _render_workflow_graph_text(
        v: WorkflowMetadata, storage: StorageInterface
    ) -> str:
        """Render a human-readable list of the workflow's constituent nodes.

        For each function/pack/unpack node with a resolved atlas_node_id, uses
        brief_description if non-empty, else the first line of docstring. Nodes not found
        in storage are silently skipped (best-effort, ADR-0012).
        """
        lines: list[str] = []
        for node in v.definition.nodes:
            if not isinstance(node, (WfFunctionNode, WfPackNode, WfUnpackNode)):
                continue

            if not node.atlas_node_id:
                continue

            try:
                artifact = storage.read(node.atlas_node_id)
            except KeyError:
                continue

            text = artifact.brief_description if artifact.brief_description else ""
            lines.append(f"- {node.id}: {text}")
        return "\n".join(lines) if lines else "(no constituent nodes resolved)"

    settings = load_settings()
    if (
        not settings.llm_api_key
        or not settings.llm_base_url
        or not settings.llm_chat_model
    ):
        raise AINotConfiguredError(
            "LLM settings (llm_api_key, llm_api_url, llm_chat_model) are not configured"
        )
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    response = await client.chat.completions.create(
        model=settings.llm_chat_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": f"""You are a search-indexing assistant for a scientific simulation workflow catalog.
Given a workflow name, its docstring, and a list of its constituent nodes, produce search-optimized descriptions as a JSON object with exactly these keys:

"summary": One concise sentence (≤20 words) that names what the workflow does, what it takes as input and what it returns.
  - Use terminology a user would type into a search box.
  - Include the workflow name or a clear paraphrase of it.

"description": 2-5 sentences that expand on the summary for semantic search embedding.
  - Describe what the workflow computes in physical or conceptual terms.
  - Mention the key processing steps implied by the node list.
  - Use natural synonyms and alternative phrasings to maximize recall.

Return only the JSON object, no other text.

Workflow name: {workflow.name}
Constituent nodes:
{_render_workflow_graph_text(workflow, storage)}
""",
            }
        ],
    )
    raw = _strip_think_tags(response.choices[0].message.content or "{}")

    class _AIWorkflowDescriptionResponse(BaseModel):
        summary: str
        description: str

    result = _AIWorkflowDescriptionResponse.model_validate(json.loads(raw))
    workflow.brief_description = result.summary
    workflow.description = result.description


async def enrich_artifact_metadata(
    artifact: StoredArtifact, storage: StorageInterface
) -> None:
    match artifact:
        case FunctionMetadata():
            await enrich_function_metadata(artifact)
        case WorkflowMetadata():
            await enrich_workflow_metadata(artifact, storage)
        case _:
            raise ValueError(f"Unexpected artifact type: {type(artifact)}")
