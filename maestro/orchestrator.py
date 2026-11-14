"""The agent graph.

A cost-aware ReAct-style loop built on LangGraph:

    START → router ─simple─→ answer → END
                  └─complex─→ agent ⇄ tools → END

- `router`: cheap model classifies the request.
- `answer`: cheap model answers directly (simple path).
- `agent`: strong model with tools bound; loops on tool calls.
- `tools`: runs MCP tools.

Nodes stay pure (they only return state updates). The streaming event loop in
`runtime.py` reads each node's output to compute cost and emit dashboard events.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

SYSTEM_PROMPT = (
    "You are Maestro, a self-hosted agentic assistant. You operate over a local "
    "knowledge base and a set of tools exposed as MCP servers. Plan, call tools when "
    "needed, and produce a concise final answer. Prefer fewer tool calls."
)

ROUTER_PROMPT = (
    "Classify the user request as 'simple' or 'complex'.\n"
    "- simple: a direct factual or creative answer with no need for tools or external data.\n"
    "- complex: requires inspecting files, searching code, running commands, or "
    "multi-step reasoning.\n"
    "Reply with exactly one word: simple or complex."
)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    route: str
    router_msg: object
    answer: str
    answer_msg: object


class Orchestrator:
    def __init__(self, router_llm, agent_llm, tools):
        self.router_llm = router_llm
        self.agent_llm = agent_llm
        self.tools = tools
        self.bound_agent = agent_llm.bind_tools(tools)
        self.graph = self._build()

    def _build(self):
        tool_node = ToolNode(self.tools)

        def router(state: AgentState):
            resp = self.router_llm.invoke(
                [SystemMessage(content=ROUTER_PROMPT), state["messages"][0]]
            )
            decision = "complex" if "complex" in (resp.content or "").strip().lower() else "simple"
            return {"route": decision, "router_msg": resp}

        def answer(state: AgentState):
            resp = self.router_llm.invoke(
                [SystemMessage(content=SYSTEM_PROMPT), state["messages"][0]]
            )
            return {"answer": resp.content, "answer_msg": resp}

        def agent(state: AgentState):
            resp = self.bound_agent.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
            return {"messages": [resp]}

        def from_router(state: AgentState):
            return "answer" if state.get("route") == "simple" else "agent"

        def from_agent(state: AgentState):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        g = StateGraph(AgentState)
        g.add_node("router", router)
        g.add_node("answer", answer)
        g.add_node("agent", agent)
        g.add_node("tools", tool_node)
        g.add_edge(START, "router")
        g.add_conditional_edges("router", from_router, {"answer": "answer", "agent": "agent"})
        g.add_edge("answer", END)
        g.add_conditional_edges("agent", from_agent, {"tools": "tools", END: END})
        g.add_edge("tools", "agent")
        return g.compile()
