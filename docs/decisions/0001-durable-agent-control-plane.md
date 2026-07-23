# ADR 0001: Durable agent control plane

Status: accepted

## Decision

Use PostgreSQL as the source of truth, a transactional outbox for work
publication, Redis Streams for delivery, and PostgreSQL-backed LangGraph
checkpoints. Treat model and tool output as untrusted data. Require explicit
approval for write/financial MCP tools.

## Consequences

The system survives process crashes and supports horizontal workers without
making Redis the authority. Delivery is at least once, so all jobs and external
side effects require idempotency. Operations are more involved than an in-process
agent, but runs, decisions, and failures are explainable and recoverable.
