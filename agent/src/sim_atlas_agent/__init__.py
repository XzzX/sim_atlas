import asyncio
import uuid

from langfuse.langchain import CallbackHandler
from langgraph.types import Command

from sim_atlas_agent.agent import get_async_agent

langfuse_handler = CallbackHandler()


async def exec():
    agent = await get_async_agent()

    thread_id = uuid.uuid4().hex

    config = {
        "callbacks": [langfuse_handler],
        "configurable": {"thread_id": thread_id},
        "metadata": {"langfuse_session_id": thread_id},
    }

    agent.update_state(config, {"graph": {"nodes": {}, "edges": []}})

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit"}:
            break

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": question,
                    }
                ]
            },
            config=config,
            version="v2",
        )

        while result.interrupts:
            pending = result.interrupts[0].value
            decisions = []
            for req in pending["action_requests"]:
                if req["name"] == "ask_user":
                    print(f"User question: {req['args']['question']}")
                    try:
                        answer = input(">").strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    decisions.append({"type": "respond", "message": answer})
                else:
                    print(f"Unknown action request: {req['name']}, rejecting")
                    decisions.append(
                        {
                            "type": "reject",
                            "message": f"unsupported action {req['name']}",
                        }
                    )
            result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config,
                version="v2",
            )

        print(result["messages"][-1].content)


asyncio.run(exec())
