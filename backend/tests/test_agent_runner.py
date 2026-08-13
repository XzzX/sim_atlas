from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import AsyncGenerator
from typing import Any, cast

import httpx
import pytest
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallUnion,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_function_tool_call import Function
from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseOutputItem,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)
from openai.types.responses.response_reasoning_item import Content

from sim_atlas.agent._runner import resolve_llm_config, run_agent_stream
from sim_atlas.agent._sse import with_keepalive
from sim_atlas.agent.tools import RESPONSES_TOOLS, TOOLS
from sim_atlas.exceptions import AINotConfiguredError
from sim_atlas.models import AgentRequest
from sim_atlas.storage_interface import StorageInterface

runner_module = importlib.import_module("sim_atlas.agent._runner")


class _FakeFilterOptions:
    datatypes: list[str] = []
    units: list[str] = []
    quantities: list[str] = []
    keywords: list[str] = []


class _FakeStorage:
    def get_filter_options(self) -> _FakeFilterOptions:
        return _FakeFilterOptions()


class _FakeSettings:
    llm_api_key = "test-key"
    llm_base_url = "http://localhost"
    llm_chat_model = "test-model"
    llm_api = "chat"
    llm_reasoning_effort = None
    agent_max_iterations = 10
    langfuse_public_key = None
    langfuse_secret_key = None
    langfuse_host = None
    langfuse_environment = None


class _ResponsesSettings(_FakeSettings):
    llm_api = "responses"


class _EffortSettings(_FakeSettings):
    llm_reasoning_effort = "none"


class _OneTurnChatSettings(_FakeSettings):
    agent_max_iterations = 1


class _OneTurnResponsesSettings(_ResponsesSettings):
    agent_max_iterations = 1


# --- fake LLM transport ---
#
# The fake sits at the HTTP layer rather than at `client.create(**kwargs)`, so
# assertions run against the JSON body the SDK actually serialises. That matters
# for the `omit` sentinel: it is passed as a kwarg either way, and only the
# serialiser decides whether the key reaches the wire -- which is the exact thing
# the gateway rejected. Scripted replies are built from real SDK models so the
# client parses them the way it parses a live response.


class _FakeAPI:
    """Routes by path, records request bodies, replays scripted replies."""

    def __init__(
        self, chat_script: list[dict[str, Any]], responses_script: list[dict[str, Any]]
    ) -> None:
        self.chat: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []
        self._chat_script = chat_script
        self._responses_script = responses_script

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = cast(dict[str, Any], json.loads(request.content))
        if request.url.path.endswith("/responses"):
            self.responses.append(body)
            script, count = self._responses_script, len(self.responses)
        else:
            self.chat.append(body)
            script, count = self._chat_script, len(self.chat)
        # The last scripted reply repeats, so a script need only cover the turns
        # a test actually cares about.
        return httpx.Response(200, json=script[min(count - 1, len(script) - 1)])


def _install_client(
    monkeypatch: pytest.MonkeyPatch,
    settings_cls: type[_FakeSettings],
    chat_script: list[ChatCompletion] | None = None,
    responses_script: list[Response] | None = None,
) -> _FakeAPI:
    """Point the runner at a mock-transport client and fake settings."""
    api = _FakeAPI(
        [
            reply.model_dump(mode="json")
            for reply in (chat_script or [_chat_response(content="Done.")])
        ],
        [
            reply.model_dump(mode="json")
            for reply in (
                responses_script or [_responses_response([_output_message()])]
            )
        ],
    )

    def make_client(api_key: str, base_url: str) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(api)),
        )

    def no_validation_errors(scratch: Any, storage: Any) -> list[str]:
        return []

    monkeypatch.setattr(runner_module, "load_settings", settings_cls)
    monkeypatch.setattr(runner_module, "AsyncOpenAI", make_client)
    monkeypatch.setattr(runner_module, "validate_graph", no_validation_errors)
    return api


def _chat_response(
    content: str | None = None,
    tool_calls: list[ChatCompletionMessageToolCallUnion] | None = None,
) -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-1",
        created=0,
        model="test-model",
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason="tool_calls" if tool_calls else "stop",
                message=ChatCompletionMessage(
                    role="assistant", content=content, tool_calls=tool_calls
                ),
            )
        ],
    )


def _chat_tool_call(
    call_id: str = "call-1",
    name: str = "search_nodes",
    arguments: str = '{"query": "x"}',
) -> ChatCompletionMessageToolCall:
    return ChatCompletionMessageToolCall(
        id=call_id,
        type="function",
        function=Function(name=name, arguments=arguments),
    )


def _responses_response(output: list[ResponseOutputItem]) -> Response:
    return Response(
        id="resp-1",
        created_at=0,
        model="test-model",
        object="response",
        output=output,
        parallel_tool_calls=False,
        tool_choice="auto",
        tools=[],
    )


def _output_message(text: str = "Done.") -> ResponseOutputMessage:
    return ResponseOutputMessage(
        id="msg-1",
        role="assistant",
        status="completed",
        type="message",
        content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
    )


def _reasoning_item(text: str = "thinking") -> ResponseReasoningItem:
    return ResponseReasoningItem(
        id="rs-1",
        type="reasoning",
        summary=[],
        content=[Content(type="reasoning_text", text=text)],
    )


def _responses_tool_call(
    call_id: str = "call-1",
    name: str = "search_nodes",
    arguments: str = '{"query": "x"}',
) -> ResponseFunctionToolCall:
    return ResponseFunctionToolCall(
        type="function_call", call_id=call_id, name=name, arguments=arguments
    )


def _collect(request: AgentRequest) -> list[str]:
    async def go() -> list[str]:
        return [
            chunk
            async for chunk in run_agent_stream(
                request,
                cast(StorageInterface, _FakeStorage()),
                resolve_llm_config(request),
            )
        ]

    return asyncio.run(go())


def _event_types(chunks: list[str]) -> list[str]:
    types: list[str] = []
    for chunk in chunks:
        if chunk.startswith("data: "):
            types.append(json.loads(chunk.removeprefix("data: "))["type"])
    return types


def test_run_agent_stream_records_tracing_without_changing_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_client(monkeypatch, _FakeSettings)

    chunks = _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert any('"type":"message"' in chunk for chunk in chunks)
    assert any('"type":"graph_update"' in chunk for chunk in chunks)


# --- endpoint selection and reasoning effort ---


def test_chat_path_omits_reasoning_effort_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The GWDG regression guard: an unknown key must not reach the wire at all.

    A gateway that has never heard of `reasoning_effort` rejects it whether the
    value is a literal null or a string, so `omit` has to keep the key absent.
    """
    api = _install_client(monkeypatch, _FakeSettings)

    _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert "reasoning_effort" not in api.chat[0]
    assert api.chat[0]["tools"] == TOOLS
    assert api.chat[0]["tool_choice"] == "auto"
    assert not api.responses


def test_chat_path_forwards_reasoning_effort_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _install_client(monkeypatch, _EffortSettings)

    _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert api.chat[0]["reasoning_effort"] == "none"


def test_responses_path_emits_the_same_sse_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two endpoints are asserted equal to each other, not to a literal."""
    request = AgentRequest(query="Hello", nodes=[], edges=[])

    _install_client(monkeypatch, _FakeSettings)
    chat_events = _event_types(_collect(request))

    api = _install_client(monkeypatch, _ResponsesSettings)
    responses_events = _event_types(_collect(request))

    assert responses_events == chat_events
    assert not api.chat
    assert api.responses[0]["tools"] == RESPONSES_TOOLS
    assert "reasoning" not in api.responses[0]


def test_responses_path_emits_a_reasoning_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reasoning is surfaced on a tool-calling turn, which is where the UI shows it."""
    _install_client(
        monkeypatch,
        _ResponsesSettings,
        responses_script=[
            _responses_response(
                [_reasoning_item("weighing options"), _responses_tool_call()]
            ),
            _responses_response([_output_message()]),
        ],
    )

    async def fake_execute_tool(*_: Any, **__: Any) -> str:
        return '{"ok": true}'

    monkeypatch.setattr(runner_module, "execute_tool", fake_execute_tool)

    chunks = _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert any(
        '"type":"reasoning"' in chunk and "weighing options" in chunk
        for chunk in chunks
    )


@pytest.mark.parametrize("api", ["chat", "responses"])
def test_tool_calls_round_trip_on_both_endpoints(
    api: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_cls = _ResponsesSettings if api == "responses" else _FakeSettings
    fake = _install_client(
        monkeypatch,
        settings_cls,
        chat_script=[
            _chat_response(tool_calls=[_chat_tool_call()]),
            _chat_response(content="Done."),
        ],
        responses_script=[
            _responses_response([_reasoning_item(), _responses_tool_call()]),
            _responses_response([_output_message()]),
        ],
    )

    async def fake_execute_tool(*_: Any, **__: Any) -> str:
        return '{"ok": true}'

    monkeypatch.setattr(runner_module, "execute_tool", fake_execute_tool)

    chunks = _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    expected = ["tool_call", "tool_result", "graph_update", "graph_update", "message"]
    if api == "responses":
        # Only the Responses API returns reasoning as a first-class item; this
        # chat turn carries no content, so there is nothing to surface.
        expected.insert(0, "reasoning")
    assert _event_types(chunks) == expected

    if api == "chat":
        second = fake.chat[1]["messages"]
        assert {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": '{"ok": true}',
        } in second
    else:
        second = fake.responses[1]["input"]
        assert {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": '{"ok": true}',
        } in second
        # Reasoning items must be echoed back: dropping one orphans the call
        # that followed it, which gateways reject on the next turn.
        assert any(item.get("type") == "reasoning" for item in second)


@pytest.mark.parametrize("api", ["chat", "responses"])
def test_turn_limit_summary_disables_tools(
    api: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_cls = (
        _OneTurnResponsesSettings if api == "responses" else _OneTurnChatSettings
    )
    fake = _install_client(
        monkeypatch,
        settings_cls,
        chat_script=[_chat_response(tool_calls=[_chat_tool_call()])],
        responses_script=[_responses_response([_responses_tool_call()])],
    )

    async def fake_execute_tool(*_: Any, **__: Any) -> str:
        return '{"ok": true}'

    monkeypatch.setattr(runner_module, "execute_tool", fake_execute_tool)

    chunks = _collect(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert "truncated" in _event_types(chunks)
    summary_call = (fake.responses if api == "responses" else fake.chat)[-1]
    assert summary_call["tool_choice"] == "none"
    assert "tools" not in summary_call


# --- SSE keep-alive ---


def test_with_keepalive_fills_silent_gaps() -> None:
    async def slow_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        await asyncio.sleep(0.25)
        yield "data: two\n\n"

    async def collect() -> list[str]:
        return [chunk async for chunk in with_keepalive(slow_events(), interval=0.05)]

    chunks = asyncio.run(collect())

    assert [c for c in chunks if c.startswith("data: ")] == [
        "data: one\n\n",
        "data: two\n\n",
    ]
    # 0.25s of silence at a 0.05s interval, with slack for a slow test machine.
    min_keepalives = 2
    assert chunks.count(": keep-alive\n\n") >= min_keepalives
    # The filler lands inside the gap, not before the first event or after the last.
    assert chunks[0] == "data: one\n\n"
    assert chunks[-1] == "data: two\n\n"


def test_with_keepalive_stays_silent_while_events_flow() -> None:
    async def fast_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        yield "data: two\n\n"

    async def collect() -> list[str]:
        return [chunk async for chunk in with_keepalive(fast_events(), interval=30.0)]

    assert asyncio.run(collect()) == ["data: one\n\n", "data: two\n\n"]


def test_with_keepalive_propagates_generator_failures() -> None:
    async def failing_events() -> AsyncGenerator[str, None]:
        yield "data: one\n\n"
        raise RuntimeError("boom")

    async def collect() -> list[str]:
        return [
            chunk async for chunk in with_keepalive(failing_events(), interval=30.0)
        ]

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(collect())


def test_with_keepalive_closes_the_agent_stream_when_the_client_leaves() -> None:
    """A disconnect must not strand the in-flight `anext` on the inner generator."""
    closed = False

    async def slow_events() -> AsyncGenerator[str, None]:
        nonlocal closed
        try:
            yield "data: one\n\n"
            await asyncio.sleep(30)
            yield "data: two\n\n"
        finally:
            closed = True

    async def take_one() -> str:
        stream = with_keepalive(slow_events(), interval=30.0)
        first = ""
        async for chunk in stream:
            first = chunk
            break
        await stream.aclose()
        return first

    assert asyncio.run(take_one()) == "data: one\n\n"
    assert closed


# --- credential resolution ---


class _NoKeySettings(_FakeSettings):
    llm_api_key = None


class _NoBaseUrlSettings(_FakeSettings):
    llm_base_url = None


class _NoModelSettings(_FakeSettings):
    llm_chat_model = None


def test_resolve_llm_config_prefers_the_request_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(
        AgentRequest(query="Hello", nodes=[], edges=[], llm_api_key="user-key")
    )

    assert llm.api_key == "user-key"
    # Neither the base URL nor the model is caller-supplied.
    assert llm.base_url == "http://localhost"
    assert llm.chat_model == "test-model"


def test_resolve_llm_config_falls_back_to_the_server_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _FakeSettings)

    llm = resolve_llm_config(AgentRequest(query="Hello", nodes=[], edges=[]))

    assert llm == ("test-key", "http://localhost", "test-model", "chat", None)


def test_resolve_llm_config_uses_the_request_key_without_a_server_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoKeySettings)

    llm = resolve_llm_config(
        AgentRequest(query="Hello", nodes=[], edges=[], llm_api_key="user-key")
    )

    assert llm == ("user-key", "http://localhost", "test-model", "chat", None)


def test_resolve_llm_config_raises_without_any_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner_module, "load_settings", _NoKeySettings)

    with pytest.raises(AINotConfiguredError):
        resolve_llm_config(AgentRequest(query="Hello", nodes=[], edges=[]))


@pytest.mark.parametrize("settings_cls", [_NoBaseUrlSettings, _NoModelSettings])
def test_resolve_llm_config_raises_when_the_server_is_incomplete(
    settings_cls: type[_FakeSettings], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller-supplied key cannot substitute for a missing base URL or model."""
    monkeypatch.setattr(runner_module, "load_settings", settings_cls)

    with pytest.raises(AINotConfiguredError):
        resolve_llm_config(
            AgentRequest(query="Hello", nodes=[], edges=[], llm_api_key="user-key")
        )
