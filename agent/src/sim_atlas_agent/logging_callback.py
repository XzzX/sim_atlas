import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import AsyncCallbackHandler

logger = logging.getLogger("sim_atlas_agent")

_TRUNCATE = 200


def _truncate(value: Any) -> str:
    text = str(value)
    if len(text) > _TRUNCATE:
        return f"{text[:_TRUNCATE]}..."
    return text


class LoggingCallbackHandler(AsyncCallbackHandler):
    """Logs agent/tool/LLM lifecycle events as they happen, for a responsive REPL."""

    def __init__(self):
        super().__init__()
        self._token_buffers: dict[UUID, list[str]] = {}

    async def on_chain_start(self, serialized, inputs, *, run_id, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "chain"
        logger.info("step start: %s input=%s", name, _truncate(inputs))

    async def on_chain_end(self, outputs, *, run_id, **kwargs):
        logger.info("step end: output=%s", _truncate(outputs))

    async def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "tool"
        logger.info("tool start: %s args=%s", name, _truncate(input_str))

    async def on_tool_end(self, output, *, run_id, **kwargs):
        logger.info("tool end: result=%s", _truncate(output))

    async def on_tool_error(self, error, *, run_id, **kwargs):
        logger.info("tool error: %s", _truncate(error))

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        model = (serialized or {}).get("name") or kwargs.get("name") or "chat model"
        count = sum(len(batch) for batch in messages)
        logger.info("llm call start: %s (%d message(s))", model, count)
        self._token_buffers[run_id] = []

    async def on_llm_new_token(self, token, *, run_id, **kwargs):
        self._token_buffers.setdefault(run_id, []).append(token)
        logger.debug("llm token: %r", token)

    async def on_llm_end(self, response, *, run_id, **kwargs):
        buffered = "".join(self._token_buffers.pop(run_id, []))
        if buffered:
            logger.info("llm call end: %s", _truncate(buffered))
        else:
            logger.info("llm call end")
