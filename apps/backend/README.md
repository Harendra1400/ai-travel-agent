# Backend

Python 3.12 FastAPI API and asynchronous worker for the AI Travel Agent.

## Layout

- `src/app/api/routes`: thin authenticated HTTP contracts.
- `src/app/services`: transaction, tenancy, idempotency, and workflow rules.
- `src/app/db/models`: normalized SQLAlchemy persistence model.
- `src/app/agents`: schema-constrained LangGraph planner and validator.
- `src/app/mcp_gateway`: deny-by-default policy and streamable-HTTP MCP client.
- `src/app/infrastructure`: Redis Streams and tenant-filtered Qdrant adapters.
- `migrations`: immutable Alembic history; never use `create_all` in deployment.
- `tests`: unit, contract, migration, security, and durability tests.

## Commands

```powershell
uv python install 3.12
uv sync --frozen --all-groups
Copy-Item .env.example .env
uv run alembic upgrade head
uv run python -m app.db.bootstrap
uv run uvicorn app.main:app --reload
uv run python -m app.worker
```

`app.db.bootstrap` is the deployment initializer: it applies Alembic and creates
the checkpoint tables owned by LangGraph. Run only one migration job at a time.

Quality gate:

```powershell
uv run black --check src tests migrations
uv run ruff check src tests migrations
uv run mypy src tests
uv run pytest
```

The suite enforces 80% aggregate coverage; critical policy and approval paths are
covered directly, while CI additionally applies, checks, downgrades, and reapplies
the schema against PostgreSQL 18.

## Runtime configuration

All variables use the `TRAVEL_AGENT_` prefix. Production requires authentication,
OIDC issuer/audience/JWKS, external database/cache/vector URLs, and an OpenAI key.
`MCP_SERVERS` and `MCP_TOOLS` are JSON values; each tool is explicitly assigned a
server, risk (`read`, `write`, or `financial`), and required scopes.

The API exposes `/health`, `/live`, `/ready`, and versioned `/v1` routes. API docs
are disabled in production.
