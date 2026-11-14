# Roadmap

The MVP is a complete, runnable loop. These are the stretch tiers — each one is an
interview talking point on its own.

## Tier 1 — Reliability & replay
- **Event stream + replay**: persist every dashboard event to an append-only log
  (e.g. a local stream / Kinesis-equivalent) so a run can be replayed step-by-step.
  Talking point: event sourcing, ordering, exactly-once vs. at-least-once.

## Tier 2 — Real memory
- **pgvector backend** for `MemoryStore`: embed documents (Bedrock Titan or a local
  model), store vectors, do semantic retrieval for the agent.
  Talking point: embeddings, chunking, recall/precision, hybrid (keyword + vector).

## Tier 3 — Observability
- **OpenTelemetry**: emit spans for router / agent / tools; export to a local collector.
- **Run a simulated Sev-1**: inject a failure (e.g. MCP tool timeout), capture the
  trace, and author a Correction of Errors (COE) doc in the repo.
  Talking point: tracing, metrics, incident response, COE discipline.

## Tier 4 — Agent quality
- **Eval harness**: score agent runs against a small task set — pass rate, cost, and
  latency — and plot regressions across model/router changes.
  Talking point: how do you *measure* an agent? golden tasks, LLM-as-judge, cost/latency
  budgets.

## Tier 5 — Deploy
- **Docker Compose** for local full-stack (app + Postgres/pgvector + collector).
- **Terraform** to deploy to AWS in one command.
  Talking point: IaC, least-privilege IAM, reproducible environments.

## Interview talking points this project demonstrates
- MCP protocol & tool design (your Amazon MCP work).
- Agentic loop: planning vs. reaction, tool-use, loop termination.
- Cost-aware LLM routing (your SageMaker→Bedrock cost-reduction work).
- Streaming events over WebSocket (your Kinesis / real-time streaming background).
- Observability & COE (your on-call / Sev-1 background).
- Sandboxed tool execution: allowlists, path confinement, timeout, blocked patterns.
