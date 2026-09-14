import ast
import json
import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import AsyncCallbackHandler

logger = logging.getLogger("sim_atlas_agent")

_TRUNCATE = 200

# Tool name -> function pulling a human headline out of its parsed args.
_TOOL_HEADLINE = {
    "search": lambda args: args.get("query"),
    "cookbook": lambda args: args.get("sim_atlas_id"),
    "detailed_node_info": lambda args: ", ".join(args.get("sim_atlas_ids", [])),
    "apply_ops": lambda args: args.get("intent"),
    "ask_user": lambda args: args.get("question"),
    "graph_view": lambda args: None,
}

# Tool name -> function summarizing its raw string output.
_TOOL_RESULT = {
    "search": lambda text: _count_lines(text, "match"),
    "cookbook": lambda text: _count_lines(text, "match"),
    "detailed_node_info": lambda text: _count_blocks(text, "node"),
}


def _truncate(value: Any) -> str:
    text = str(value)
    if len(text) > _TRUNCATE:
        return f"{text[:_TRUNCATE]}..."
    return text


def _count_lines(text: str, noun: str) -> str:
    n = len([line for line in text.splitlines() if line.strip()])
    if n == 0:
        return f"no {noun}es"
    return f"{n} {noun}{'es' if n != 1 else ''}"


def _count_blocks(text: str, noun: str) -> str:
    n = len([b for b in text.split("\n\n===\n\n") if b.strip()])
    return f"{n} {noun}{'s' if n != 1 else ''}"


def _first_line(text: str) -> str:
    for line in str(text).splitlines():
        if line.strip():
            return _truncate(line.strip())
    return ""


def _parse_args(input_str: Any) -> dict:
    # LangChain passes dict-shaped tool input as str(dict) (Python repr, not JSON)
    # when the tool takes more than one argument.
    if isinstance(input_str, dict):
        return input_str
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(input_str)
        except (TypeError, ValueError, SyntaxError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _headline(name: str, input_str: Any) -> str:
    args = _parse_args(input_str)
    fn = _TOOL_HEADLINE.get(name)
    if fn is not None:
        # known tool: trust its choice of headline (or lack thereof), e.g. graph_view has none
        value = fn(args)
    elif args:
        value = next(iter(args.values()), None)
    else:
        # unknown, single-argument tool: LangChain passes the bare value, not a dict
        value = input_str
    return f"{name}: {_truncate(value)}" if value else name


def _result_summary(name: str, output: Any) -> str:
    text = str(output)
    fn = _TOOL_RESULT.get(name)
    if fn is not None:
        return fn(text)
    return _first_line(text)


def _reasoning_from_kwargs(kwargs: dict | None) -> str:
    if not kwargs:
        return ""
    return kwargs.get("reasoning_content") or kwargs.get("reasoning") or ""


class LoggingCallbackHandler(AsyncCallbackHandler):
    """Narrates agent/tool/LLM activity as short, human-readable lines."""

    def __init__(self):
        super().__init__()
        self._tool_starts: dict[UUID, tuple[str, float]] = {}
        self._llm_starts: dict[UUID, float] = {}
        self._reasoning: dict[UUID, list[str]] = {}
        self._content: dict[UUID, list[str]] = {}

    async def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        self._tool_starts[run_id] = (name, time.monotonic())
        logger.info(_headline(name, input_str))

    async def on_tool_end(self, output, *, run_id, **kwargs):
        name, started = self._tool_starts.pop(run_id, ("tool", time.monotonic()))
        elapsed = time.monotonic() - started
        logger.info("  → %s (%.1fs)", _result_summary(name, output), elapsed)

    async def on_tool_error(self, error, *, run_id, **kwargs):
        name, started = self._tool_starts.pop(run_id, ("tool", time.monotonic()))
        elapsed = time.monotonic() - started
        logger.info("  ✗ %s failed: %s (%.1fs)", name, _truncate(error), elapsed)

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        self._llm_starts[run_id] = time.monotonic()
        self._reasoning[run_id] = []
        self._content[run_id] = []

    async def on_llm_new_token(self, token, *, run_id, chunk=None, **kwargs):
        if token:
            self._content.setdefault(run_id, []).append(token)
        message = getattr(chunk, "message", None)
        reasoning = _reasoning_from_kwargs(getattr(message, "additional_kwargs", None))
        if reasoning:
            self._reasoning.setdefault(run_id, []).append(reasoning)

    async def on_llm_end(self, response, *, run_id, **kwargs):
        started = self._llm_starts.pop(run_id, time.monotonic())
        elapsed = time.monotonic() - started
        reasoning = "".join(self._reasoning.pop(run_id, []))
        if not reasoning:
            for generation in getattr(response, "generations", []) or []:
                for gen in generation:
                    message = getattr(gen, "message", None)
                    reasoning = _reasoning_from_kwargs(
                        getattr(message, "additional_kwargs", None)
                    )
                    if reasoning:
                        break
                if reasoning:
                    break
        if reasoning:
            logger.info("thinking: %s (%.1fs)", _truncate(reasoning), elapsed)

        # The assistant's actual words (as opposed to its reasoning) are printed
        # in full, unlike everything else above — a real reply isn't truncated.
        content = "".join(self._content.pop(run_id, [])).strip()
        if content:
            logger.info(content)
