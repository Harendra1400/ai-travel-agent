# Security guidance

## Required production controls

1. Use an OIDC provider with MFA and short-lived access tokens. Backend issuer,
   audience, and JWKS settings must exactly match the frontend client.
2. Generate `AUTH_SECRET` with at least 32 cryptographically random bytes.
3. Put database, Redis, Qdrant, OpenAI, OIDC, and MCP secrets in a managed secret
   store. Never commit generated Kubernetes Secret YAML or `.env` files.
4. Configure separate service identities and least-privilege network policies.
5. Register only required MCP tools. Classify any external mutation as `write`
   and any reservation/payment/charge as `financial`.
6. Require provider idempotency keys for booking/payment tools and reconcile
   uncertain outcomes before retrying.
7. Terminate TLS at a trusted ingress and restrict backend trusted hosts/CORS.
8. Redact PII in supplier adapters. Do not place passport data, payment card data,
   bearer tokens, or raw provider responses in model prompts, memory, or logs.

## Payment boundary

The repository models payment state but intentionally does not handle card
numbers. Integrate a PCI-compliant payment provider using hosted/tokenized payment
flows. Store only provider references and sanitized status. A payment tool is
always `financial`, always approval-gated, and must be idempotent.

## Prompt/tool security

Memory and MCP responses are delimited as untrusted context. The model cannot
grant itself permissions: server/tool/risk come from configuration. Approval is
bound to a specific versioned payload and expires. Review any supplier adapter
for SSRF, redirect, schema-bomb, and oversized-response behavior.

## Data retention

Define retention periods for conversations, audit events, tool payloads, and
memories. The memory delete endpoint removes both Qdrant and PostgreSQL records.
Production privacy deletion should be implemented as an audited background
workflow covering backups and downstream provider obligations.

## Threats to test before launch

- Cross-tenant IDs on every route and vector query.
- Expired/replayed approval decisions.
- Duplicate queue delivery and provider timeout after an uncertain write.
- JWT algorithm, issuer, audience, and key-rotation failures.
- Prompt injection in user memory and MCP output.
- Oversized/chunked bodies at ingress and provider responses in the MCP gateway.
- Database/Redis/Qdrant partial outages and restoration from backups.
- Dependency/image vulnerabilities and provenance verification.

## Incident response

Revoke provider and OIDC credentials first, then disable affected MCP allow-list
entries. Preserve append-only audit events and request/run IDs. Do not delete
failed tool calls before reconciliation. Follow the operations runbook for queue
recovery and rollback.
