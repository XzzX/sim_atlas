import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Literal, NamedTuple

from openai.types.shared.reasoning_effort import ReasoningEffort
from pydantic import ValidationError

from sim_atlas.agent._llm import create_backend
from sim_atlas.agent._observability import (
    AsyncOpenAI,  # pyright: ignore[reportPrivateImportUsage]
    Langfuse,
    propagate_attributes,
)
from sim_atlas.agent._prompt import build_system_prompt
from sim_atlas.agent._sse import (
    ErrorEvent,
    GraphUpdateEvent,
    MessageEvent,
    ReasoningEvent,
    ToolCallEvent,
    ToolResultEvent,
    TruncatedEvent,
    ValidationEvent,
    to_sse,
)
from sim_atlas.agent.tools import (
    ScratchGraph,
    ToolError,
    execute_tool,
    validate_graph,
)
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.models import AgentRequest
from sim_atlas.settings import load_settings
from sim_atlas.storage_interface import StorageInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LLMConfig(NamedTuple):
    """Fully resolved LLM connection details for a single agent run."""

    api_key: str
    base_url: str
    chat_model: str
    api: Literal["chat", "responses"] = "chat"
    reasoning_effort: ReasoningEffort = None


def resolve_llm_config(request: AgentRequest) -> LLMConfig:
    """Resolve the LLM credentials to use for `request`.

    A caller-supplied API key wins over the server configuration, so a user can
    spend their own key. The base URL and model are deliberately not
    caller-supplied: forwarding an arbitrary URL would turn this endpoint into an
    SSRF vector, and the model is pinned to whatever the operator provisioned.

    Raises:
        AINotConfiguredError: When neither the request nor the server provides a
            complete set of credentials.
    """
    settings = load_settings()
    api_key = request.llm_api_key or settings.llm_api_key
    chat_model = settings.llm_chat_model
    base_url = settings.llm_base_url
    if not (api_key and base_url and chat_model):
        raise AINotConfiguredError(
            "No LLM credentials available: the server must provide llm_base_url and "
            "llm_chat_model, and an llm_api_key must come from either the request "
            "or the server"
        )
    return LLMConfig(
        api_key=api_key,
        base_url=base_url,
        chat_model=chat_model,
        api=settings.llm_api,
        reasoning_effort=settings.llm_reasoning_effort,
    )


def _graph_update_event(scratch: ScratchGraph) -> GraphUpdateEvent:
    return GraphUpdateEvent(
        nodes=[n.model_dump(exclude_none=True) for n in scratch.nodes.values()],
        edges=[e.model_dump() for e in scratch.edges],
    )


async def run_agent_stream(
    request: AgentRequest,
    storage: StorageInterface,
    llm: LLMConfig,
) -> AsyncGenerator[str, None]:
    """Async generator that streams SSE events while running the agent loop."""
    settings = load_settings()
    lf = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        environment=settings.langfuse_environment,
    )
    session_id = request.session_id or str(uuid.uuid4())
    final_message: str | None = None
    correction_rounds = 0
    total_input_tokens = 0
    total_output_tokens = 0
    max_turns = settings.agent_max_iterations
    with (
        lf.start_as_current_observation(
            as_type="agent",
            name="workflow-builder",
            input=request.query,
        ) as root_span,
        propagate_attributes(user_id=request.user_id, session_id=session_id),
    ):
        try:
            # Setup lives inside the try because the response headers are flushed
            # before this generator first runs: an exception escaping here would
            # abort an already-started 200 rather than surface as an error.
            client = AsyncOpenAI(api_key=llm.api_key, base_url=llm.base_url)
            scratch = ScratchGraph(request.nodes, request.edges)
            backend = create_backend(
                client,
                llm.api,
                llm.chat_model,
                llm.reasoning_effort,
                build_system_prompt(request, storage),
                request,
            )

            # Runaway-check loop: exits naturally (break) when the agent finishes,
            # or falls through (no break) when the turn limit is reached.
            for _ in range(max_turns):
                turn = await backend.turn()
                total_input_tokens += turn.input_tokens
                total_output_tokens += turn.output_tokens

                if not turn.tool_calls:
                    final_message = turn.text or "(no response)"
                    with lf.start_as_current_observation(
                        name="graph_validation"
                    ) as span:
                        validation_errors = validate_graph(scratch, storage)
                        span.update(
                            output={"errors": validation_errors},
                        )
                        if not validation_errors:
                            break
                    # Emit a validation event so the UI can show a correction round.
                    yield to_sse(ValidationEvent(errors=validation_errors))
                    correction_rounds += 1
                    error_text = "\n".join(f"- {e}" for e in validation_errors)
                    logger.debug(
                        "Graph validation errors (stream); asking agent to correct:\n%s",
                        error_text,
                    )
                    backend.add_user_message(
                        "The current graph has validation errors. "
                        "Please fix them using the available tools:\n" + error_text
                    )
                    continue

                reasoning = turn.reasoning or turn.text
                if reasoning:
                    yield to_sse(ReasoningEvent(content=reasoning))
                for call in turn.tool_calls:
                    args: dict[str, Any] = json.loads(call.arguments)
                    yield to_sse(ToolCallEvent(name=call.name, args=args))

                    try:
                        content = await execute_tool(call.name, args, storage, scratch)
                    except (ValidationError, ToolError) as exc:
                        msg = (
                            f"Invalid arguments for '{call.name}': {exc}"
                            if isinstance(exc, ValidationError)
                            else str(exc)
                        )
                        content = json.dumps({"error": msg})

                    yield to_sse(ToolResultEvent(name=call.name, content=content))
                    backend.add_tool_result(call.id, content)

                yield to_sse(_graph_update_event(scratch))

            truncated = final_message is None
            if truncated:
                # Turn limit reached without natural completion.
                # Make one tool-free summary call so the history entry is honest.
                backend.add_user_message(
                    "You have reached the maximum number of turns. "
                    "Summarise in 2-3 sentences: what you have built so far "
                    "and what still needs to be done to fulfil the original request. "
                    "End with a clear statement of the next step the user should ask you to take."
                )

                summary = await backend.turn(use_tools=False)
                final_message = summary.text or "(turn limit reached)"
                total_input_tokens += summary.input_tokens
                total_output_tokens += summary.output_tokens
                logger.debug("Turn limit reached; summary: %s", final_message)

            root_span.update(
                output=final_message,
                metadata={
                    "llm_api": llm.api,
                    "reasoning_effort": llm.reasoning_effort,
                    "correction_rounds": correction_rounds,
                    "truncated": truncated,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                },
            )
            yield to_sse(_graph_update_event(scratch))
            yield to_sse(MessageEvent(content=final_message))
            if truncated:
                yield to_sse(TruncatedEvent())

            lf.flush()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent stream error")
            root_span.update(level="ERROR", status_message=str(exc))
            yield to_sse(ErrorEvent(message=str(exc)))
        finally:
            lf.flush()
