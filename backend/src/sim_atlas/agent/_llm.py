"""Endpoint adapter: `/v1/chat/completions` vs `/v1/responses`.

Gateways disagree about how to combine reasoning with function tools. Some
apply a default reasoning effort and then reject tools on
`/v1/chat/completions`, demanding `/v1/responses` instead; others (GWDG) only
implement `/v1/chat/completions` at all. The agent loop is written once against
`LLMBackend`, and only the request/response marshalling differs per endpoint.

Each backend owns the running transcript. That is what keeps the loop single:
appending an assistant turn is the largest shape difference between the two
APIs -- chat appends one message, while Responses must echo back the entire
typed output list, reasoning items included.
"""

import json
import logging
from typing import Any, Literal, NamedTuple, Protocol, cast

from openai import AsyncOpenAI, omit
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
)
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseFunctionToolCall,
    ResponseInputItemParam,
    ResponseReasoningItem,
)
from openai.types.responses.response_input_item_param import FunctionCallOutput
from openai.types.shared.reasoning_effort import ReasoningEffort
from openai.types.shared_params import Reasoning

from sim_atlas.agent.tools import RESPONSES_TOOLS, TOOLS
from sim_atlas.models import AgentRequest

logger = logging.getLogger(__name__)


class ToolCall(NamedTuple):
    id: str
    name: str
    arguments: str  # raw JSON, parsed by the caller


class Turn(NamedTuple):
    """One assistant turn, normalised across both endpoints."""

    text: str | None
    reasoning: str | None
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int


class LLMBackend(Protocol):
    async def turn(self, *, use_tools: bool = True) -> Turn: ...

    def add_user_message(self, content: str) -> None: ...

    def add_tool_result(self, call_id: str, content: str) -> None: ...


class _ChatBackend:
    """`/v1/chat/completions` -- the default, and the only endpoint GWDG serves."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        reasoning_effort: ReasoningEffort,
        system_prompt: str,
        request: AgentRequest,
    ) -> None:
        self._client = client
        self._model = model
        # Annotated: inference would widen the literals to `str`, which the SDK
        # parameter will not accept.
        self._effort: ReasoningEffort = reasoning_effort
        history: list[ChatCompletionMessageParam] = [
            cast(ChatCompletionMessageParam, {"role": m.role, "content": m.content})
            for m in request.history
        ]
        self._messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": request.query},
        ]

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_tool_result(self, call_id: str, content: str) -> None:
        self._messages.append(
            {"role": "tool", "tool_call_id": call_id, "content": content}
        )

    async def turn(self, *, use_tools: bool = True) -> Turn:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            tools=TOOLS if use_tools else omit,
            tool_choice="auto" if use_tools else "none",
            # `or omit` keeps the key out of the body entirely when unset: a
            # literal null is not the same thing to a gateway that has never
            # heard of the parameter.
            reasoning_effort=self._effort or omit,
        )
        message = response.choices[0].message
        logger.debug(
            "LLM response message: %s",
            json.dumps(message.model_dump(exclude_unset=True), indent=2),
        )
        self._messages.append(
            cast(ChatCompletionMessageParam, message.model_dump(exclude_unset=True))
        )
        # A non-standard extra that some gateways return alongside the content.
        raw_reasoning: Any = getattr(message, "reasoning", None)
        usage = response.usage
        return Turn(
            text=message.content,
            reasoning=raw_reasoning if isinstance(raw_reasoning, str) else None,
            tool_calls=[
                ToolCall(tc.id, tc.function.name, tc.function.arguments)
                for tc in message.tool_calls or []
                if isinstance(tc, ChatCompletionMessageToolCall)
            ],
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


class _ResponsesBackend:
    """`/v1/responses` -- required by gateways that refuse tools alongside reasoning."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        reasoning_effort: ReasoningEffort,
        system_prompt: str,
        request: AgentRequest,
    ) -> None:
        self._client = client
        self._model = model
        # Annotated: inference would widen the literals to `str`, which the SDK
        # parameter will not accept.
        self._effort: ReasoningEffort = reasoning_effort
        self._input: list[ResponseInputItemParam] = [
            EasyInputMessageParam(role="system", content=system_prompt),
            *(
                EasyInputMessageParam(role=m.role, content=m.content)
                for m in request.history
            ),
            EasyInputMessageParam(role="user", content=request.query),
        ]

    def add_user_message(self, content: str) -> None:
        self._input.append(EasyInputMessageParam(role="user", content=content))

    def add_tool_result(self, call_id: str, content: str) -> None:
        self._input.append(
            FunctionCallOutput(
                type="function_call_output", call_id=call_id, output=content
            )
        )

    async def turn(self, *, use_tools: bool = True) -> Turn:
        response = await self._client.responses.create(
            model=self._model,
            input=self._input,
            tools=RESPONSES_TOOLS if use_tools else omit,
            tool_choice="auto" if use_tools else "none",
            reasoning=Reasoning(effort=self._effort) if self._effort else omit,
        )
        output = [
            item.model_dump(mode="json", exclude_unset=True) for item in response.output
        ]
        logger.debug("LLM response output: %s", json.dumps(output, indent=2))
        # The whole output goes back in, not just the tool calls: dropping a
        # reasoning item orphans the call that followed it, which gateways
        # reject outright on the next turn.
        self._input.extend(cast(ResponseInputItemParam, item) for item in output)

        reasoning_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for item in response.output:
            if isinstance(item, ResponseReasoningItem):
                # Models populate one or the other depending on whether they
                # expose summaries or raw reasoning text.
                reasoning_parts.extend(s.text for s in item.summary)
                reasoning_parts.extend(c.text for c in item.content or [])
            elif isinstance(item, ResponseFunctionToolCall):
                tool_calls.append(ToolCall(item.call_id, item.name, item.arguments))

        usage = response.usage
        return Turn(
            text=response.output_text or None,
            reasoning="\n".join(reasoning_parts) or None,
            tool_calls=tool_calls,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )


def create_backend(
    client: AsyncOpenAI,
    llm_api: Literal["chat", "responses"],
    model: str,
    reasoning_effort: ReasoningEffort,
    system_prompt: str,
    request: AgentRequest,
) -> LLMBackend:
    if llm_api == "responses":
        return _ResponsesBackend(
            client, model, reasoning_effort, system_prompt, request
        )
    return _ChatBackend(client, model, reasoning_effort, system_prompt, request)
