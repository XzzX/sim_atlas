import os

from deepagents import create_deep_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from sim_atlas_agent.prompts import system_prompt
from sim_atlas_agent.tools import ask_user
from sim_atlas_agent.tools.wf import GraphState, apply_ops, graph_view

model = ChatOpenAI(
    model=os.environ["SIM_ATLAS_LLM_MODEL"],
    base_url=os.environ["SIM_ATLAS_LLM_URL"],
    api_key=os.environ["SIM_ATLAS_LLM_KEY"],
)


async def get_mcp_tools():
    client = MultiServerMCPClient(
        {
            "docs-langchain": {
                "transport": "http",
                "url": "http://127.0.0.1:8000/mcp/",
            }
        }
    )
    tools = await client.get_tools()

    print(f"\ndocs-langchain: {len(tools)} tool(s)")
    for t in tools:
        print(f"  {t.name}")
        print(f"  {t.description[:90]}")
    return tools


async def get_async_agent():
    mcp_tools = await get_mcp_tools()

    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=[ask_user, graph_view, apply_ops, *mcp_tools],
        checkpointer=MemorySaver(),
        interrupt_on={
            "ask_user": {"allowed_decisions": ["respond"]},
        },
        state_schema=GraphState,
        debug=True,
    )

    return agent
