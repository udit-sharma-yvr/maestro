"""Runtime: owns the MCP client, models, orchestrator, and the streaming event loop."""

import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .config import settings
from .cost import CostTracker
from .llm import agent_model, router_model
from .orchestrator import Orchestrator


class Runtime:
    def __init__(self) -> None:
        self.orchestrator: Orchestrator | None = None
        self.cost: CostTracker | None = None

    async def start(self) -> None:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            {
                "filesystem": {
                    "transport": "stdio",
                    "command": settings.mcp_server_cmd,
                    "args": settings.mcp_server_args.split(),
                    "env": {"MAESTRO_SANDBOX_ROOT": str(settings.sandbox_root.resolve())},
                }
            }
        )
        tools = await client.get_tools()
        self.cost = CostTracker()
        self.orchestrator = Orchestrator(router_model(), agent_model(), tools)

    async def run_task(self, task_id: str, prompt: str):
        """Async generator yielding dashboard events for one task."""
        yield _ev("task.start", task_id=task_id, prompt=prompt)

        state = {"messages": [HumanMessage(content=prompt)]}
        route = None
        last_answer = ""
        answer_emitted = False

        try:
            async for update in self.orchestrator.graph.astream(state, stream_mode="updates"):
                node = next(iter(update))
                payload = update[node] or {}

                if node == "router":
                    route = payload.get("route")
                    bd = self.cost.add(settings.router_model, _usage(payload.get("router_msg")))
                    yield _ev("route", decision=route, model=settings.router_model, cost=_cost_dict(bd))

                elif node == "answer":
                    bd = self.cost.add(settings.router_model, _usage(payload.get("answer_msg")))
                    last_answer = payload.get("answer", "")
                    answer_emitted = True
                    yield _ev("answer", content=last_answer, model=settings.router_model, cost=_cost_dict(bd))

                elif node == "agent":
                    for m in payload.get("messages", []):
                        if isinstance(m, AIMessage):
                            if _usage(m):
                                bd = self.cost.add(settings.agent_model, _usage(m))
                                yield _ev(
                                    "agent.message",
                                    content=m.content,
                                    tool_calls=_tool_calls(m),
                                    model=settings.agent_model,
                                    cost=_cost_dict(bd),
                                )
                            if not getattr(m, "tool_calls", None):
                                last_answer = m.content

                elif node == "tools":
                    for m in payload.get("messages", []):
                        if isinstance(m, ToolMessage):
                            yield _ev(
                                "tool.result",
                                name=m.name,
                                tool_call_id=m.tool_call_id,
                                result=_trunc(m.content),
                            )

                yield _ev("cost", total=self.cost.snapshot())

            if route == "complex" and not answer_emitted:
                yield _ev("answer", content=last_answer)

            yield _ev("task.end", answer=last_answer, cost=self.cost.snapshot())

        except Exception as e:  # surfaced to the dashboard, not the server log only
            yield _ev("error", message=f"{type(e).__name__}: {e}")


def _ev(type_: str, **fields) -> dict:
    return {"type": type_, "ts": time.time(), **fields}


def _usage(msg) -> dict:
    um = getattr(msg, "usage_metadata", None) or {}
    return {"input_tokens": um.get("input_tokens", 0), "output_tokens": um.get("output_tokens", 0)}


def _cost_dict(bd) -> dict:
    return {
        "model": bd.model,
        "input_tokens": bd.input_tokens,
        "output_tokens": bd.output_tokens,
        "input_cost": round(bd.input_cost, 6),
        "output_cost": round(bd.output_cost, 6),
        "total_cost": round(bd.total_cost, 6),
    }


def _tool_calls(m) -> list[dict]:
    return [{"name": tc.get("name"), "args": tc.get("args")} for tc in (getattr(m, "tool_calls", None) or [])]


def _trunc(s, n: int = 2000) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"\n…[truncated {len(s) - n} chars]"
