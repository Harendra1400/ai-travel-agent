# Operations runbook

## Deployment order

1. Provision managed PostgreSQL, Redis, and Qdrant with encryption, backups,
   private networking, and monitoring.
2. Create `backend-secrets` and `frontend-secrets` from the secret manager.
3. Patch image names/tags, domains, OIDC values, resources, and replicas.
4. Apply the namespace/configuration.
5. Run the `database-migration` Job and require a successful completion.
6. Roll out workers, backend, then frontend.
7. Verify `/live`, `/ready`, login, a no-tool plan, approval rejection, and one
   sandbox MCP read.

Never run application pods with a schema older than their minimum supported
migration. Use expand/contract migrations for zero-downtime changes.

## Rollback

Roll back images to the previous immutable tag. Do not automatically downgrade
the database: migrations may be destructive or old code may not understand new
data. Each release must document schema compatibility. Restore a database only
after isolating writers and confirming the recovery point.

## Alerts

Alert on:

- API readiness failures or elevated 5xx/latency.
- Worker crash loops and Redis pending-entry age/count.
- Outbox events in `failed` or `processing` beyond the dispatch threshold.
- Agent/tool failure rate and approvals waiting near expiry.
- PostgreSQL saturation, replica lag, deadlocks, and backup failures.
- Redis memory/evictions/persistence failures.
- Qdrant latency/indexing failure and collection size anomalies.
- OpenAI/MCP latency, rate limit, authentication, and schema errors.

## Queue recovery

Workers reclaim idle Redis entries automatically after 60 seconds. If a queue is
stalled:

1. Check PostgreSQL run/tool state before changing Redis.
2. Confirm at least one healthy worker and valid Redis consumer group.
3. Inspect pending entries and their idle time.
4. Restart workers; do not delete pending entries.
5. If republishing from the outbox, leave idempotency constraints enabled and
   reconcile any external write whose result is uncertain.

## Database recovery

Test point-in-time restore quarterly. Restore into an isolated environment, run
`alembic current`, validate row counts/constraints, then test application
readiness and representative tenant queries. LangGraph checkpoint tables are
created by the bootstrap job and must be included in backup policy.

## Secret rotation

Rotate OIDC/MCP/provider secrets with overlapping validity where supported.
Restart workloads after the secret version changes. Database/Redis credentials
may require staged users. Verify old credentials fail after the rollout.

## Qdrant rebuild

PostgreSQL memory rows are authoritative. If the Qdrant collection is lost,
recreate it with the configured dimension/distance and enqueue every active
memory for re-embedding/indexing. Keep the service available with memory retrieval
degraded rather than treating vector data as durable truth.
