# Production environment

This directory intentionally contains no credentials. Before applying the base
manifests, create `backend-secrets` and `frontend-secrets` from the deployment
platform's secret manager and patch host names, image names, resource limits, and
replica counts for the target cluster.

Required backend secret keys:

- `TRAVEL_AGENT_DATABASE_URL`
- `TRAVEL_AGENT_REDIS_URL`
- `TRAVEL_AGENT_QDRANT_URL`
- `TRAVEL_AGENT_QDRANT_API_KEY` when required
- `TRAVEL_AGENT_OPENAI_API_KEY`
- `TRAVEL_AGENT_AUTH_ISSUER`
- `TRAVEL_AGENT_AUTH_AUDIENCE`
- `TRAVEL_AGENT_AUTH_JWKS_URL`
- MCP bearer-token environment variables referenced by configured servers

Required frontend secret keys:

- `AUTH_SECRET`
- `AUTH_CLIENT_SECRET`

Run the migration Job to completion before rolling out backend or worker images.
