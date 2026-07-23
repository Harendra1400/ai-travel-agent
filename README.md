# AI Travel Agent

A production-oriented reference platform for durable, human-governed AI travel
planning. The repository contains a FastAPI API and worker, a Next.js web
application, PostgreSQL migrations, Redis Streams, Qdrant semantic memory,
LangGraph orchestration, an allow-listed MCP gateway, OIDC authentication, and
deployment manifests.

The platform plans trips and can call configured external MCP tools. It does not
ship with a travel supplier, payment processor, identity tenant, or cloud account;
those are environment-specific integrations and credentials.

## How a request works

1. Auth.js completes OIDC Authorization Code + PKCE and stores an encrypted,
   HTTP-only session.
2. The Next.js same-origin proxy adds the server-held access token to API calls.
3. FastAPI verifies the JWT, tenant-scopes every query, and writes a queued
   `agent_run` plus outbox event in one PostgreSQL transaction.
4. A worker publishes the outbox event to Redis Streams and executes LangGraph
   with PostgreSQL checkpoints.
5. The planner retrieves tenant-filtered Qdrant memory and returns a
   schema-constrained plan, itinerary items, and optional MCP tool requests.
6. Read tools execute asynchronously. Write and financial tools stop at an
   expiring, versioned human approval.
7. Tool results are fed into the next planning pass. A validated result becomes
   a versioned itinerary the user can accept.

See [system architecture](docs/architecture/system.md) for diagrams and trust
boundaries.

## Repository map

```text
.
├── apps/
│   ├── backend/                 FastAPI API, worker, models, migrations, tests
│   └── frontend/                Next.js App Router application and OIDC proxy
├── docs/
│   ├── architecture/            System and database design
│   ├── decisions/               Architecture decision records
│   └── operations/              Deployment and incident runbook
├── infrastructure/
│   ├── environments/            Environment-specific deployment guidance
│   └── orchestration/           Kustomize/Kubernetes production baseline
├── .github/workflows/           CI and signed multi-platform image releases
├── docker-compose.yml           Secret-driven local integration environment
└── .env.example                 Local Compose variable contract
```

## Local start

Prerequisites: Docker Compose and an OpenAI API key.

```powershell
Copy-Item .env.example .env
# Replace every placeholder in .env.
docker compose up --build
```

`database-init` applies Alembic migrations and initializes LangGraph checkpoint
tables before the API and worker start. The web application is served on
`http://127.0.0.1:3000`; API liveness and readiness are available at `/live` and
`/ready`.

Local Compose deliberately disables authentication and binds data services to
loopback. The backend refuses `AUTH_DISABLED=true` when its environment is
`production`.

## Verify without containers

Backend, from `apps/backend`:

```powershell
uv sync --frozen --all-groups
uv run black --check src tests migrations
uv run ruff check src tests migrations
uv run mypy src tests
uv run pytest
```

Frontend, from `apps/frontend`:

```powershell
pnpm install --frozen-lockfile
pnpm lint
$env:AUTH_DISABLED="true"
pnpm build
```

## Production deployment

Release tags build multi-architecture, SBOM-attached images in GitHub Actions.
Before applying [the Kubernetes baseline](infrastructure/orchestration/platform.yaml):

1. Patch image registry/tag and public host names.
2. Provision highly available managed PostgreSQL, Redis, and Qdrant.
3. Create the documented Kubernetes secrets from an external secret manager.
4. Configure an OIDC client and matching backend issuer/audience/JWKS settings.
5. Configure exact MCP server/tool allow lists and secret environment references.
6. Run the migration Job and require success before rolling out API/worker pods.
7. Connect JSON logs and Kubernetes metrics to the organization’s observability
   stack and validate backup restoration.

The [operations runbook](docs/operations/runbook.md) contains rollout,
rollback, recovery, and alert guidance.

## Security model

- Deny-by-default MCP tool allow list and centrally assigned risk classes.
- Human approval for write and financial side effects.
- OIDC JWT validation, inactive-account denial, tenant filters, and no automatic
  cross-issuer account linking.
- Credentials supplied only by runtime environment/secret manager.
- Immutable audit records, idempotency keys, transactional outbox, Redis pending
  message recovery, and PostgreSQL LangGraph checkpoints.
- Structured JSON logs with request IDs and generic client-facing agent errors.
- Non-root, read-only Kubernetes containers with resource bounds and probes.

Review [security guidance](docs/security.md) before connecting real suppliers or
processing payment data.
