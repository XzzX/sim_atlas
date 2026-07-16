import logging
import re
from http import HTTPStatus

from sim_atlas_toolkit import node_store_api
from sim_atlas_toolkit.models import (
    Annotation,
    WfDefinition,
    WfFunctionNode,
    WfInputNode,
    WfOutputNode,
    artifact_response_adapter,
)
from sim_atlas_toolkit.settings import ToolkitSettings

logger = logging.getLogger(__name__)

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"\A```[^\n]*\n(.*?)\n```\Z", re.DOTALL)
_QUOTES = ('"""', "'''", '"', "'")


def clean_response(content: str) -> str:
    """Strip reasoning tags, code fences, and wrapping quotes from an LLM reply.

    Args:
        content: The raw message content returned by the LLM.

    Returns:
        The cleaned docstring text.
    """
    # Drop <think>...</think> reasoning blocks emitted by reasoning models.
    content = _THINK_BLOCK.sub("", content)
    # Some reasoning models omit the opening tag; keep only what follows the
    # final closing tag.
    if "</think>" in content:
        content = content.rsplit("</think>", 1)[-1]
    content = content.strip()

    # Unwrap a fenced code block (```python ... ```), if the model added one.
    if match := _CODE_FENCE.match(content):
        content = match.group(1).strip()

    # Unwrap surrounding quotes the model may have wrapped the docstring in.
    for quote in _QUOTES:
        if (
            len(content) >= 2 * len(quote)
            and content.startswith(quote)
            and content.endswith(quote)
        ):
            content = content[len(quote) : -len(quote)].strip()
            break

    return content


async def generate_docstring(
    settings: ToolkitSettings, source_code: str, docstring: str
) -> str:
    """Generate a docstring for the given source code using an LLM, if enabled.

    Args:
        settings: Toolkit settings; gates whether generation runs
            (``llm_enabled``, ``llm_overwrite``) and provides the LLM client
            config.
        source_code: The source code to generate a docstring for.
        docstring: The existing docstring, if any.

    Returns:
        The generated docstring, or ``docstring`` unchanged if generation is
        disabled, unnecessary (a docstring already exists and
        ``llm_overwrite`` is not set), or the LLM call fails.
    """
    should_generate = (
        settings.llm_enabled
        and bool(source_code)
        and (settings.llm_overwrite or not docstring)
    )
    if not should_generate:
        return docstring

    try:
        from openai import AsyncOpenAI  # noqa: PLC0415

        client = AsyncOpenAI(api_key=settings.llm_key, base_url=settings.llm_url)

        prompt = f"""
You are a technical writer generating Python docstrings. You will receive
Python source code for a single function, method, or class.

Your task: write a docstring for it in NumPy style.

Rules:

1. If the code already contains a docstring, use it as the basis. Keep its
   wording and intent where possible, but verify every statement against the
   actual code. Correct anything that is wrong, outdated, or inconsistent
   with the implementation (e.g., parameters that no longer exist, wrong
   types, wrong default values, described behavior that differs from the code).
2. If there is no docstring, derive one entirely from the code itself. Do
   not invent behavior that cannot be inferred from the implementation or
   signature. If a parameter's purpose is genuinely unclear, describe it
   neutrally based on how it is used.
3. The docstring must contain exactly these sections, in this order:
   - A one-line summary (imperative mood, ends with a period, fits on one
     line, no leading "This function ...").
   - A blank line, then an extended description: one short paragraph
     explaining what the code does, relevant behavior, and side effects.
     Omit this only if the function is trivial and the summary says it all.
   - A "Parameters" section describing every parameter in signature order.
     Use type annotations from the signature if present. Note defaults as
     ", optional" with the default mentioned in the description
     (e.g., "by default 10"). Skip self and cls.
   - A "Returns" section describing the return value(s) with type and
     meaning. If the function returns None, omit this section. For
     generators, use "Yields" instead.
4. Drop everything else. Do not include Raises, Examples, Notes, See Also,
   References, or any other sections, even if the original docstring had
   them.
5. Formatting: NumPy style with underlined section headers, e.g.

   Parameters
   ----------
   x : int
       Description of x.

   Wrap lines at 79 characters. Indent continuation lines of descriptions
   by four spaces relative to the parameter name.
6. Output only the docstring, without the triple quotes, with no
   surrounding code, no markdown fences, and no commentary.

Source code:

<code>
{source_code}
</code>
"""

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        return (clean_response(content) if content else "") or docstring
    except Exception:
        logger.exception("LLM docstring generation failed")
        return docstring


def _format_boundary_node(ann: Annotation) -> str:
    details: list[str] = []
    if ann.datatype:
        details.append(f"datatype: {ann.datatype}")
    if ann.has_default_value:
        details.append("optional")
    if ann.description:
        details.append(ann.description)
    if details:
        return f"- {ann.label}: {', '.join(details)}"
    return f"- {ann.label}"


async def _render_function_node(api_url: str, node: WfFunctionNode) -> str:
    brief = None
    display_name = node.node_id
    if node.atlas_id is not None:
        try:
            response = await node_store_api.read_artifact(api_url, node.atlas_id)
            if response.status_code == HTTPStatus.OK:
                artifact = artifact_response_adapter.validate_python(response.json())
                display_name = artifact.name
                brief = artifact.brief_description or next(
                    (p for p in (artifact.docstring or "").split("\n\n") if p.strip()),
                    None,
                )
        except Exception:
            logger.exception(
                "Failed to fetch node info for %s (%s)", node.node_id, node.atlas_id
            )

    header = (
        f"- {node.node_id} [{display_name}]: {brief or '(no description available)'}"
    )
    input_labels = "; ".join(a.label for a in node.inputs if a.label)
    output_labels = "; ".join(a.label for a in node.outputs if a.label)
    return f"{header}\n  inputs: {input_labels}\n  outputs: {output_labels}"


async def _render_wf_graph(api_url: str, wf_definition: WfDefinition) -> str:
    """Render a workflow's dataflow graph as text for the LLM prompt.

    Function nodes are enriched with their stored name and description,
    fetched via ``node_store_api.read_artifact`` using ``atlas_id``. Nodes
    that cannot be resolved are rendered with just their id and I/O labels.
    """
    input_nodes = [n for n in wf_definition.nodes if isinstance(n, WfInputNode)]
    output_nodes = [n for n in wf_definition.nodes if isinstance(n, WfOutputNode)]
    function_nodes = [n for n in wf_definition.nodes if isinstance(n, WfFunctionNode)]

    lines = ["Inputs:"]
    lines.extend(
        _format_boundary_node(ann) for node in input_nodes for ann in node.outputs
    )

    lines.append("")
    lines.append("Function nodes:")
    for node in function_nodes:
        lines.append(await _render_function_node(api_url, node))

    lines.append("")
    lines.append("Outputs:")
    lines.extend(
        _format_boundary_node(ann) for node in output_nodes for ann in node.inputs
    )

    lines.append("")
    lines.append("Data flow:")
    for edge in wf_definition.edges:
        source = edge.source_node + (f".{edge.source_port}" if edge.source_port else "")
        target = edge.target_node + (f".{edge.target_port}" if edge.target_port else "")
        lines.append(f"- {source} -> {target}")

    return "\n".join(lines)


async def generate_workflow_docstring(
    settings: ToolkitSettings,
    name: str,
    source_code: str,
    docstring: str,
    wf_definition: WfDefinition,
) -> str:
    """Generate a docstring for a workflow from its source and dataflow graph, if enabled.

    Args:
        settings: Toolkit settings; gates whether generation runs
            (``llm_enabled``, ``llm_overwrite``) and provides the LLM client
            config and the backend API URL used to fetch per-node descriptions.
        name: The workflow's name.
        source_code: The workflow's rendered Python source code.
        docstring: The workflow's existing docstring, if any.
        wf_definition: The parsed dataflow graph, used to describe the
            workflow's constituent nodes and how data flows between them.

    Returns:
        The generated docstring, or ``docstring`` unchanged if generation is
        disabled, unnecessary (a docstring already exists and
        ``llm_overwrite`` is not set), or the LLM call fails.
    """
    should_generate = settings.llm_enabled and (settings.llm_overwrite or not docstring)
    if not should_generate:
        return docstring

    try:
        from openai import AsyncOpenAI  # noqa: PLC0415

        client = AsyncOpenAI(api_key=settings.llm_key, base_url=settings.llm_url)
        graph = await _render_wf_graph(settings.api_url, wf_definition)

        prompt = f"""
You are a technical writer generating Python docstrings. You will receive a
description of a scientific simulation workflow: its name, its rendered
Python source code, any existing docstring, and its dataflow graph -- the
constituent function nodes (each with a short description of what it does
and its inputs and outputs) and the data-flow edges connecting them.

Your task: write a docstring for the workflow in NumPy style.

Rules:

1. If an existing docstring is provided, use it as the basis. Keep its
   wording and intent where possible, but verify every statement against
   the source code and the dataflow graph. Correct anything that is wrong,
   outdated, or inconsistent with them.
2. If there is no existing docstring, derive one entirely from the source
   code and the graph. Describe what the workflow computes end to end:
   what the inputs represent, which processing steps run (follow the
   data-flow edges for their order), and what the outputs represent. Use
   the node descriptions to explain the steps in domain terms rather than
   by function name alone. Do not invent behavior that cannot be inferred
   from the provided information.
3. The docstring must contain exactly these sections, in this order:
   - A one-line summary (imperative mood, ends with a period, fits on one
     line, no leading "This workflow ...").
   - A blank line, then an extended description: one short paragraph
     summarizing the computational pipeline in domain terms -- the key
     steps and how data flows between them.
   - A "Parameters" section describing every workflow input, in the given
     order. Note inputs that have a default value as ", optional".
   - A "Returns" section describing every workflow output with its
     meaning.
4. Do not include Raises, Examples, Notes, See Also, References, or any
   other sections.
5. Formatting: NumPy style with underlined section headers, e.g.

   Parameters
   ----------
   x : int
       Description of x.

   Wrap lines at 79 characters. Indent continuation lines of descriptions
   by four spaces relative to the parameter name.
6. Output only the docstring, without the triple quotes, with no
   surrounding code, no markdown fences, and no commentary.

Workflow name: {name}

Existing docstring:
<docstring>
{docstring or "(none)"}
</docstring>

Source code:
<code>
{source_code}
</code>

Dataflow graph:
<graph>
{graph}
</graph>
"""

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        return (clean_response(content) if content else "") or docstring
    except Exception:
        logger.exception("LLM workflow docstring generation failed for %s", name)
        return docstring
