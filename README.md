# Maestro

**Self-hosted agentic assistant — MCP tools, streaming reasoning, live observability.**

Maestro is a small but production-shaped agent platform. You point it at a knowledge
base (a directory of files) and ask it to plan and execute multi-step tasks —
summarize code, find TODOs, investigate a file. It classifies the request, reasons
with an LLM, calls tools exposed as an **MCP** server, and streams its step-by-step
reasoning plus live token cost to a browser dashboard.

## Architecture

```
┌────────────┐   POST /run    ┌──────────────┐
│  Dashboard │ ─────────────▶ │  FastAPI     │
│  (browser) │ ◀── WS stream ─│  server      │
└────────────┘   events        └──────┬───────┘
                                     │ builds
                                     ▼
                          ┌──────────────────────┐
                          │  Orchestrator        │
                          │  (LangGraph)         │
                          │  router → agent ⇄ tools
                          └──────┬───────────────┘
                                 │ tool calls (MCP, stdio)
                                 ▼
                          ┌──────────────────────┐
                          │  MCP filesystem      │
                          │  read_file /          │
                          │  search_code /        │
                          │  run_command          │
                          └──────┬───────────────┘
                                 │ operates within
                                 ▼
                          ┌──────────────────────┐
                          │  sandbox/ (dir)      │
                          └──────────────────────┘
```

**Cost-aware routing:** a cheap "router" model classifies each request. Simple
questions are answered directly by the cheap model. Anything needing tools or
multi-step reasoning runs the strong "agent" model in a tool-use loop. Per-call token
usage is priced and streamed to the dashboard.

## Project layout

```
maestro/
├── maestro/                 # the agent platform (Python)
│   ├── config.py            # env-driven settings
│   ├── llm.py               # provider factory (anthropic | openai | bedrock)
│   ├── cost.py              # per-model pricing + CostTracker
│   ├── memory.py            # memory interface + in-memory store
│   ├── orchestrator.py      # LangGraph: router → agent ⇄ tools
│   ├── runtime.py           # MCP client + streaming event loop
│   ├── server.py            # FastAPI: POST /run, WS /stream/{id}, dashboard
│   └── __main__.py          # entrypoint
├── mcp_tools/
│   └── filesystem.py        # MCP server: read_file / search_code / run_command
├── dashboard/               # static HTML/JS/CSS — live reasoning + cost view
├── sandbox/                 # the workspace the MCP tools operate within
├── pyproject.toml
├── .env.example
└── ROADMAP.md
```

## Quick start

Requires Python 3.11+ and an API key for one provider (Anthropic, OpenAI, or AWS
Bedrock).

```bash
cd maestro
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env
# edit .env: set MAESTRO_LLM_PROVIDER and the matching API key

maestro            # starts the server on http://127.0.0.1:8000
```

Open http://127.0.0.1:8000, type a prompt, and watch the reasoning stream in.

Try: `Read sandbox/notes.md and summarize the TODOs.`

## How it works

1. **`POST /run`** creates a task and starts the orchestrator in the background.
2. The **router** node calls the cheap model to classify the request as `simple` or
   `complex`.
3. `simple` → the cheap model answers directly and the task ends.
4. `complex` → the **agent** node calls the strong model with tools bound. If it emits
   tool calls, the **tools** node runs them (via the MCP server) and loops back to the
   agent; otherwise the task ends.
5. Every node update is streamed over **`WS /stream/{task_id}`** as JSON events:
   `route`, `agent.message`, `tool.result`, `cost`, `answer`, `task.end`.
6. The **dashboard** renders the timeline and a live cost counter.

## Configuration

All settings are env-prefixed `MAESTRO_` (see `.env.example`):

| Setting | Default | Purpose |
|---|---|---|
| `MAESTRO_LLM_PROVIDER` | `anthropic` | `anthropic` \| `openai` \| `bedrock` |
| `MAESTRO_ROUTER_MODEL` | `claude-3-5-haiku-20241022` | cheap model for routing + simple answers |
| `MAESTRO_AGENT_MODEL` | `claude-3-5-sonnet-20241022` | strong model for tool-use reasoning |
| `MAESTRO_SANDBOX_ROOT` | `sandbox` | directory the MCP filesystem tools operate within |
| `MAESTRO_HOST` / `MAESTRO_PORT` | `127.0.0.1` / `8000` | server bind |

Provider keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or AWS credentials for Bedrock.

## Roadmap

See `ROADMAP.md` — event stream + replay, pgvector memory, OpenTelemetry tracing, an
eval harness, and one-command AWS deploy via Terraform.

## License

MIT
