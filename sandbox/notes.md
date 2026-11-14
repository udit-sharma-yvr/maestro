# Project notes

Open work:
- TODO: add pgvector-backed semantic memory (replace InMemoryStore).
- TODO: add OpenTelemetry tracing spans to the orchestrator nodes.
- TODO: persist the event stream so runs can be replayed.

Design:
- The router model (cheap) classifies requests; the agent model (strong) does tool-use.
- Cost is tracked per LLM call and streamed live to the dashboard.
- MCP tools are confined to this sandbox directory.
