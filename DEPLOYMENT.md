# Deployment

Three reference recipes, picked to cover the stack space most companies actually have. Pick the one that matches the user's existing cloud; the docs after assume Postgres + pgvector as the data store per [`STORAGE.md`](./STORAGE.md).

## Component inventory (what gets deployed)

| Component | Role | Typical host |
|---|---|---|
| Postgres + pgvector | Data store | Supabase, Neon, RDS, Cloud SQL |
| MCP server | Agent-facing read/write API over MCP | Fly, Railway, Cloud Run, ECS, K8s |
| REST API | Backplane for Web UI, Slack bot, ingestion | Same host as MCP server (same process is fine) |
| Web UI | Admin, search, review queue | Vercel |
| Slack/Teams bot | Contribution surface | Vercel serverless, Cloud Run, or a small worker |
| Ingestion workers | Scheduled scrapers | Cloud Scheduler + Cloud Run, EventBridge + Lambda, or a cron job in your k8s |
| OIDC provider | Human auth | Clerk, Auth0, Descope, or company SSO |
| Embedding API | Vector generation | Voyage AI, OpenAI, Anthropic (with caching) |

All components are optional at v0 except Postgres, MCP server, and an OIDC provider. Web UI and Slack bot can follow.

## Recipe A: Vercel-centric (cheapest, fastest) — RECOMMENDED

Best for small-to-mid teams, greenfield, or shops already using Vercel for web.

| Component | Host | Cost |
|---|---|---|
| Postgres + pgvector | **Supabase** or **Neon** free tier | $0 |
| MCP server + REST API | **Fly.io** (shared-cpu-1x, 256MB RAM) | ~$2/mo |
| Web UI | **Vercel** (hobby or team) | $0–$20/mo |
| Slack bot | **Vercel serverless** | $0 |
| OIDC | **Clerk** free tier | $0 |
| Embeddings | **Voyage AI** (voyage-3) or OpenAI | ~$0.02/1K entries/mo |

**Total: $0–$25/mo at 10K–50K entries.**

Deployment steps (the agent walks through these):

1. `supabase projects create lexicon-<company>` (or Neon equivalent)
2. Enable `pgvector` extension in the SQL editor: `CREATE EXTENSION vector;`
3. Deploy schema from [`PRIMITIVES.md`](./PRIMITIVES.md) via a migration tool (Alembic, Drizzle, Prisma — implementation choice)
4. Deploy MCP + REST server to Fly: `fly launch` with the supplied `Dockerfile`, set env vars (see below)
5. Deploy Web UI to Vercel: `vercel link` then `vercel --prod`
6. Configure Clerk app, set OIDC redirect URL to Vercel deployment
7. Create Slack app, add bot to workspace, deploy Slack serverless handler to Vercel
8. Set DNS CNAME: `lexicon.company.internal` → Fly app, `lexicon-ui.company.internal` → Vercel
9. Distribute MCP client config (see below) to employees

## Recipe B: AWS enterprise

For shops with existing AWS standards, VPC requirements, or compliance constraints.

| Component | Host | Cost |
|---|---|---|
| Postgres + pgvector | **RDS PostgreSQL 16** (db.t4g.micro → db.t4g.small) | $15–$60/mo |
| MCP + REST server | **ECS Fargate** or **App Runner** (0.5 vCPU, 1GB) | $20–$40/mo |
| Web UI | **CloudFront + S3** (static) or **Amplify** | $5–$15/mo |
| Slack bot | **Lambda + API Gateway** | ~$1/mo |
| Ingestion workers | **EventBridge + Lambda** or scheduled ECS tasks | ~$5/mo |
| OIDC | **Cognito** or company IdP via SAML | $0–$50/mo |
| Embeddings | same as Recipe A |

**Total: $50–$200/mo at 10K–50K entries.**

Key differences from Recipe A:
- Everything in a VPC
- Secrets in Secrets Manager
- IAM-gated DB access from compute
- CloudWatch for logs + metrics
- Terraform/CloudFormation IaC preferred for reproducibility

## Recipe C: Azure / GCP / self-hosted Kubernetes

For shops standardized on Azure or GCP, or with a k8s platform team.

- **Postgres + pgvector:** Azure Database for PostgreSQL Flexible Server / Cloud SQL for PostgreSQL / CNPG operator on your cluster
- **MCP + REST server:** Container Apps / Cloud Run / a k8s Deployment
- **Web UI:** Static Web Apps / Cloud Run / k8s Deployment fronted by an Ingress
- **Ingestion workers:** Container Apps Jobs / Cloud Scheduler + Cloud Run Jobs / k8s CronJobs

The shape is the same across all three; the provider-specific wiring is boilerplate the agent generates.

## Environment variables

Expected by the MCP server + REST API:

```bash
# Storage
LEXICON_DATABASE_URL=postgresql://lexicon:***@host:5432/lexicon

# Auth
LEXICON_OIDC_ISSUER_URL=https://clerk.your-company.com
LEXICON_OIDC_CLIENT_ID=***
LEXICON_OIDC_CLIENT_SECRET=***
LEXICON_SERVICE_TOKEN_HMAC_SECRET=***  # for signing service tokens

# Embeddings
LEXICON_EMBEDDING_PROVIDER=voyage  # voyage | openai | anthropic
LEXICON_EMBEDDING_MODEL=voyage-3
LEXICON_EMBEDDING_API_KEY=***

# Operations
LEXICON_LOG_LEVEL=info
LEXICON_OTLP_ENDPOINT=https://otel.your-observability.com
LEXICON_SENTRY_DSN=***

# Ingestion (only workers need these)
LEXICON_NOTION_TOKEN=***
LEXICON_CONFLUENCE_TOKEN=***
LEXICON_SLACK_TOKEN=***
LEXICON_SALESFORCE_CLIENT_ID=***
LEXICON_SALESFORCE_CLIENT_SECRET=***
LEXICON_ANTHROPIC_API_KEY=***  # for LLM-driven ingestion classifier
```

**Never commit these.** Use the hosting provider's secret store.

## DNS and TLS

- MCP server: `lexicon-mcp.company.internal` (internal DNS only; not public)
- REST + Web UI: `lexicon.company.internal` (internal) or `lexicon.company.com` (public with SSO gate)
- TLS: managed via the hosting provider (Fly/Vercel/ECS all handle it)
- **Do not expose the MCP server publicly without auth.** Per-user tokens are required but prefer internal-only DNS as defense in depth.

## CI/CD

The reference CI pipeline (agent generates for the chosen stack):

1. **On PR:** lint, typecheck, unit tests, schema diff check against main
2. **On merge to main:** build container, push to registry, deploy to staging
3. **Manual promote to prod:** after staging smoke tests pass
4. **Post-deploy:** run Alembic migrations (or equivalent) against prod DB, wait for health check, flip traffic
5. **Embedding re-hydration:** if the migration changed primitive schemas that affect `search_text`, kick off a background job to re-embed affected rows

## Client configuration distribution

Once the service is live, IT pushes an MCP config to every employee's LLM client. Three distribution strategies:

### Strategy 1: MDM / device management
Push a config file to each managed device. Claude Desktop config:

```json
{
  "mcpServers": {
    "lexicon": {
      "transport": "http",
      "url": "https://lexicon-mcp.company.internal",
      "headers": {
        "Authorization": "Bearer ${LEXICON_TOKEN}"
      }
    }
  }
}
```

### Strategy 2: Self-service onboarding page
Employee visits `https://lexicon.company.internal/onboard`, authenticates via SSO, gets a one-time download of a per-user token and a copy-paste config block. Best UX for companies without strong MDM.

### Strategy 3: Shared internal MCP gateway
Run an internal MCP gateway that authenticates users via SSO header injection and proxies to the Context Store. Employees configure one MCP server URL; the gateway handles per-user identity. Good for large enterprises with existing internal API gateways.

## Health checks

- MCP server: `GET /healthz` returns `{status: "ok", db: "ok", embedder: "ok"}`
- REST API: same
- Postgres: use the hosting provider's native check
- **Synthetic check:** every 5 min from a known location, call `lexicon.search("test")` and assert non-error response

## Rollout sequence

Recommended order for a fresh deployment:

1. **Week 1:** provision infra, apply schema, deploy MCP + REST, validate with a hand-seeded entry via curl
2. **Week 1–2:** deploy Web UI behind SSO, onboard 3–5 curators as pilot users
3. **Week 2:** wire Slack bot for pilot team
4. **Week 2–3:** run the first ingestion pass (see [`INGESTION.md`](./INGESTION.md)) against one source (likely the team's existing glossary or dbt project), curators triage the proposal queue
5. **Week 3–4:** push MCP client config to the pilot team, observe real agent queries against the seeded data
6. **Week 4+:** broader rollout, add more ingestion sources, onboard non-technical contributors via Slack

Do not launch to the whole company before the first audit log shows that real agent queries are returning sensible grounded answers for the pilot team.
