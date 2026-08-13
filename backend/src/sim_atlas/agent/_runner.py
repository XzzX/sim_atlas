import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any, NamedTuple, cast

from openai import omit
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)
from pydantic import ValidationError

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
    TOOLS,
    ScratchGraph,
    ToolError,
    execute_tool,
    validate_graph,
)
from sim_atlas.exceptions import AINotConfiguredError, LLMSelectionError
from sim_atlas.llm_providers import ReasoningEffort
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
    reasoning_effort: ReasoningEffort | None = None


#: `AsyncOpenAI` refuses an empty api_key, so unauthenticated providers (a local
#: Ollama, say) get a placeholder that the endpoint will ignore.
_UNUSED_API_KEY = "none"


def resolve_llm_config(request: AgentRequest) -> LLMConfig:
    """Resolve the provider, model and credentials to use for `request`.

    The API key always comes from the caller: the server's own `llm_api_key` is
    reserved for docstring enrichment behind an access token, so an anonymous
    caller can never spend the operator's credits here.

    The provider is a caller-supplied *id* looked up in the operator's allowlist,
    never a URL, so no caller string reaches the HTTP client and this endpoint
    cannot be aimed at an arbitrary host. The model must be one the selected
    provider offers. See ADR-0019.

    Raises:
        LLMSelectionError: When the provider id or model is not allowlisted, or
            the caller supplied no API key for a provider that needs one.
        AINotConfiguredError: When the server has no providers configured at all.
    """
    settings = load_settings()
    catalog = settings.llm_catalog
    if not catalog:
        raise AINotConfiguredError(
            "This server has no LLM providers configured, so the agent cannot run"
        )

    provider_id = request.llm_provider or settings.llm_default_provider
    if provider_id is None:
        provider = next(iter(catalog.values()))
    elif (found := catalog.get(provider_id)) is not None:
        provider = found
    else:
        # Names only the allowlist, never the rejected value: this string is
        # returned to the caller.
        raise LLMSelectionError(
            f"Unknown LLM provider. Allowed providers: {', '.join(catalog)}"
        )

    if request.llm_chat_model is None:
        model = provider.resolved_default_model
    elif (chosen := provider.get_model(request.llm_chat_model)) is not None:
        model = chosen
    else:
        raise LLMSelectionError(
            f"Unknown model for provider {provider.id!r}. Allowed models: "
            f"{', '.join(m.name for m in provider.models)}"
        )

    if provider.requires_api_key:
        if not request.llm_api_key:
            raise LLMSelectionError(
                f"The agent runs on your own API key. Provide llm_api_key for "
                f"provider {provider.id!r}."
            )
        api_key = request.llm_api_key
    else:
        api_key = request.llm_api_key or _UNUSED_API_KEY

    # Dropped rather than rejected when unsupported: a selection left over in a
    # user's browser must not break a run after the catalog changes.
    reasoning_effort = request.llm_reasoning_effort if model.reasoning_effort else None
    return LLMConfig(
        api_key=api_key,
        base_url=provider.base_url,
        chat_model=model.name,
        reasoning_effort=reasoning_effort,
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
            # `omit` rather than None: None is a real value the SDK serialises, and
            # an explicit null trips up servers that do not know the parameter.
            reasoning_effort = llm.reasoning_effort or omit
            scratch = ScratchGraph(request.nodes, request.edges)

            history_messages: list[ChatCompletionMessageParam] = [
                cast(ChatCompletionMessageParam, {"role": m.role, "content": m.content})
                for m in request.history
            ]
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": build_system_prompt(request, storage)},
                *history_messages,
                {"role": "user", "content": request.query},
            ]

            # Runaway-check loop: exits naturally (break) when the agent finishes,
            # or falls through (no break) when the turn limit is reached.
            for _ in range(max_turns):
                response = await client.chat.completions.create(
                    model=llm.chat_model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    reasoning_effort=reasoning_effort,
                )
                choice = response.choices[0]
                logger.debug(
                    "LLM response message: %s",
                    json.dumps(choice.message.model_dump(exclude_unset=True), indent=2),
                )
                if response.usage:
                    total_input_tokens += response.usage.prompt_tokens
                    total_output_tokens += response.usage.completion_tokens
                messages.append(
                    cast(
                        ChatCompletionMessageParam,
                        choice.message.model_dump(exclude_unset=True),
                    )
                )

                if not choice.message.tool_calls:
                    final_message = choice.message.content or "(no response)"
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
                    correction_message = (
                        "The current graph has validation errors. "
                        "Please fix them using the available tools:\n" + error_text
                    )
                    messages.append({"role": "user", "content": correction_message})
                    continue

                reasoning = (
                    getattr(choice.message, "reasoning", None)
                    or choice.message.content
                    or None
                )
                if reasoning:
                    yield to_sse(ReasoningEvent(content=reasoning))
                for tc in choice.message.tool_calls:
                    if not isinstance(tc, ChatCompletionMessageToolCall):
                        continue
                    args: dict[str, Any] = json.loads(tc.function.arguments)
                    yield to_sse(ToolCallEvent(name=tc.function.name, args=args))

                    try:
                        result = await execute_tool(
                            tc.function.name, args, storage, scratch
                        )
                        content = result
                    except (ValidationError, ToolError) as exc:
                        msg = (
                            f"Invalid arguments for '{tc.function.name}': {exc}"
                            if isinstance(exc, ValidationError)
                            else str(exc)
                        )
                        content = json.dumps({"error": msg})

                    yield to_sse(
                        ToolResultEvent(name=tc.function.name, content=content)
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": content,
                        }
                    )

                yield to_sse(_graph_update_event(scratch))

            truncated = final_message is None
            if truncated:
                # Turn limit reached without natural completion.
                # Make one tool-free summary call so the history entry is honest.
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have reached the maximum number of turns. "
                            "Summarise in 2-3 sentences: what you have built so far "
                            "and what still needs to be done to fulfil the original request. "
                            "End with a clear statement of the next step the user should ask you to take."
                        ),
                    }
                )

                summary_response = await client.chat.completions.create(
                    model=llm.chat_model,
                    messages=messages,
                    tool_choice="none",
                    reasoning_effort=reasoning_effort,
                )
                summary_choice = summary_response.choices[0]
                final_message = summary_choice.message.content or "(turn limit reached)"
                if summary_response.usage:
                    total_input_tokens += summary_response.usage.prompt_tokens
                    total_output_tokens += summary_response.usage.completion_tokens
                logger.debug("Turn limit reached; summary: %s", final_message)

            root_span.update(output=final_message)
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
