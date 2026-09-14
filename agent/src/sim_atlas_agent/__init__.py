import asyncio
import logging
import uuid

import flowrep as fr
from langfuse.langchain import CallbackHandler
from langgraph.types import Command

from sim_atlas_agent.agent import get_async_agent
from sim_atlas_agent.flowrep import graph_to_flowrep
from sim_atlas_agent.logging_callback import LoggingCallbackHandler

logging.basicConfig(level=logging.WARNING, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("sim_atlas_agent")
logger.setLevel(logging.INFO)

langfuse_handler = CallbackHandler()


class Agent:
    def __init__(self):
        self.thread_id = uuid.uuid4().hex
        self.agent = None
        self.result = None
        # Action requests from the current interrupt still awaiting an answer, and
        # the decisions already collected for it. None when nothing is pending.
        self._pending_requests = None
        self._pending_decisions = []
        self._started = False

    async def exec(self, prompt):
        self.agent = await get_async_agent() if not self.agent else self.agent

        config = {
            "callbacks": [langfuse_handler, LoggingCallbackHandler()],
            "configurable": {"thread_id": self.thread_id},
            "metadata": {"langfuse_session_id": self.thread_id},
        }

        if self._pending_requests is not None:
            # `prompt` is the user's answer to the last ask_user question, not a
            # new message: resume the interrupted run instead of starting one.
            self._pending_decisions.append({"type": "respond", "message": prompt})
            self._pending_requests.pop(0)
            if self._next_pending_question() is not None:
                return
            self.result = await self.agent.ainvoke(
                Command(resume={"decisions": self._pending_decisions}),
                config=config,
                version="v2",
            )
            self._pending_decisions = []
        else:
            if not self._started:
                # GraphState.graph has no default, so the very first turn on this
                # thread must seed it; later turns keep building on it.
                self.agent.update_state(config, {"graph": {"nodes": {}, "edges": []}})
                self._started = True
            self.result = await self.agent.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]
                },
                config=config,
                version="v2",
            )

        while self.result.interrupts:
            self._pending_requests = list(self.result.interrupts[0].value["action_requests"])
            self._pending_decisions = []
            if self._next_pending_question() is not None:
                return
            self.result = await self.agent.ainvoke(
                Command(resume={"decisions": self._pending_decisions}),
                config=config,
                version="v2",
            )
            self._pending_decisions = []

        self._pending_requests = None

    def _next_pending_question(self):
        # Rejects leading non-ask_user requests in place, then returns the next question.
        while self._pending_requests:
            req = self._pending_requests[0]
            if req["name"] == "ask_user":
                logger.info("User question: %s", req["args"]["question"])
                return req["args"]["question"]
            logger.info("Unknown action request: %s, rejecting", req["name"])
            self._pending_decisions.append(
                {"type": "reject", "message": f"unsupported action {req['name']}"}
            )
            self._pending_requests.pop(0)
        return None

    def get_graph(self):
        return self.result.value["graph"]

    async def get_flowrep(self):
        return await graph_to_flowrep("http://127.0.0.1:8000/api/v1", self.result.value["graph"])

    async def print_flowrep(self):
        g = await self.get_flowrep()
        unreferenced_recipe = g.model_copy(update={"reference": None})
        rendered = fr.tools.flowrep2python(unreferenced_recipe)
        print("================")
        print(rendered.source)
