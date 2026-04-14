# Run: 01-vercel-greenfield (2026-04-13, claude-sonnet-4)

## Agent output

# 1. What lexicon is and why centralized

Lexicon is a company-wide Context Store: a centralized service that holds your internal terminology, tool registry, canonical queries, guardrails, and decisions, and serves them over MCP so every AI client grounds itself in your organization before answering. The repo is a spec, not a library — your agent generates the code. You need the centralized-service shape specifically because ground truth cannot fork: a markdown-in-git or per-laptop SQLite setup means a salesperson, a data engineer, and a CI job all see different definitions of "active customer," non-technical contributors can't submit terms without git, and there's no audit log or approval workflow. One deployment, one endpoint, one answer.

# 2. Storage decision

**Postgres + pgvector on Supabase free tier.** Per `STORAGE.md` §Decision matrix, "Vercel shop, no DB yet" routes to Supabase/Neon one-click. Your existing Supabase footprint makes it a zero-new-vendor choice. At 10K-50K entries (~50-200MB), pgvector gives you ACID across primitives for audit/approval/versioning, cross-primitive SQL joins, and $0 cost on free tier. Mongo Atlas and Elastic are rejected because you don't already run them and ops complexity isn't justified at 40-person scale. Commit a two-sentence ADR to your infra repo documenting the choice.

# 3. Deployment steps (this afternoon)

1. **Provision DB:** In Supabase, create project `lexicon-<company>`. In SQL editor run `CREATE EXTENSION IF NOT EXISTS vector;` then verify with `SELECT extname FROM pg_extension WHERE extname='vector';`. Capture the connection string as `LEXICON_DATABASE_URL`.
2. **Deploy schema:** Have the agent generate Drizzle migrations (TS shop, matches Vercel/Next.js) from `PRIMITIVES.md` — six primitive tables, six `*_versions` tables, one `audit_log` table, B-tree/GIN/IVFFlat indexes, version-copy triggers. Apply and verify empty tables.
3. **Deploy MCP+REST server to Fly.io:** Generate a Node + Hono + `@modelcontextprotocol/sdk` server exposing MCP (SSE/HTTP) and REST in one container. `fly launch`, set all env vars from `DEPLOYMENT.md` (database URL, OIDC, embedding key, HMAC secret). Hit `/healthz` — expect `{status:"ok", db:"ok"}`.
4. **Deploy Web UI to Vercel:** Next.js + shadcn/ui app. Ship Home/search and the `/onboard` token page first; primitive CRUD, review queue, audit viewer, admin can follow this week.
5. **Wire Clerk auth:** Create Clerk app, enable Google Workspace as the identity provider (this is your de-facto SSO), set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` on Vercel, point `LEXICON_OIDC_ISSUER_URL` at Clerk on Fly. Log in first — you become bootstrap admin.
6. **DNS:** Point `lexicon.company.com` (Vercel, public, SSO-gated) and `lexicon-mcp.company.internal` (Fly, internal DNS only) appropriately. Never expose MCP publicly.
7. **Seed one entry** via curl against REST to confirm write→audit→read round-trip works end-to-end.
8. **Self-service onboarding:** hit `/onboard`, mint your token, paste the generated Claude Desktop config block, restart Claude, ask it `search lexicon for test`. Expect a well-formed empty response.
9. **Pilot (3-10 engineers):** have them onboard via the same page this week. Observe audit log.

Defer to next week: Slack bot, broad rollout, dbt ingestion pass (narrow scope — one dbt project, triage first 20-50 proposals together with curators).

# 4. Services to sign up for

- **Supabase** (Postgres + pgvector, free tier)
- **Fly.io** (MCP + REST container, ~$2/mo)
- **Vercel** (you have this — Web UI + Slack bot serverless)
- **Clerk** (OIDC, free tier, federate to Google Workspace)
- **Voyage AI** or OpenAI (embeddings, ~$0.02/1K entries/mo)
- **Anthropic API** (ingestion classifier later)

Total: roughly $0-$25/month.

# 5. What NOT to do at launch

- Do not skip the review queue or auto-publish anything. No ingestion source has earned ≥0.9 precision yet.
- Do not deploy without per-user tokens — even "internal only." Shared tokens destroy the audit log.
- Do not put the MCP server on public DNS. Internal DNS + per-user auth, both layers.
- Do not fire-hose ingestion: no "vibe-classify our whole Notion" on day one. Start with one dbt project.
- Do not copy an old DB dump over live data — breaks audit continuity.
- Do not skip the ADR or the curator triage session before expanding ingestion.
- Do not roll out company-wide before the pilot's audit log shows sensible grounded answers for a week.

# 6. Specialist docs consulted

- `README.md`
- `.claude/skills/setup-lexicon.md`
- `ARCHITECTURE.md` (centralized-service principle, component diagram)
- `STORAGE.md` (decision matrix, scale assumption, Postgres+pgvector rationale)
- `DEPLOYMENT.md` (Recipe A Vercel-centric, env vars, client config distribution)
- `AUTH.md` (Clerk + Google Workspace, per-user tokens, bootstrap admin)

---EVAL METADATA---

Files read:
- /Users/Adam.Lenning/repos/personal/lexicon/README.md
- /Users/Adam.Lenning/repos/personal/lexicon/.claude/skills/setup-lexicon.md
- /Users/Adam.Lenning/repos/personal/lexicon/ARCHITECTURE.md
- /Users/Adam.Lenning/repos/personal/lexicon/STORAGE.md
- /Users/Adam.Lenning/repos/personal/lexicon/DEPLOYMENT.md
- /Users/Adam.Lenning/repos/personal/lexicon/AUTH.md

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | Centralized-service explanation | PASS | "Ground truth cannot fork" — exact spec language. Contrasts with markdown-in-git and SQLite. Cites the principle. |
| 2 | Storage pick: Supabase + pgvector | PASS | Explicit; names free tier. |
| 3 | Storage reasoning cites STORAGE.md | PASS | Cites §Decision matrix, scale assumption, ACID/joins/free-tier rationale. |
| 4 | Deploy plan follows setup-lexicon.md phases | PASS | Covers phases 2–9 in order: storage → schema → MCP+REST → Web UI → auth → DNS → first entry → onboarding → pilot. |
| 5 | Auth: Clerk (or peer) | PASS | Clerk with Google Workspace as the identity provider. |
| 6 | MCP server host: Fly.io | PASS | Explicit; names small cost. |
| 7 | Warns against auto-publish | PASS | "Do not skip the review queue or auto-publish anything." First bullet in §5. |
| 8 | Narrow first ingestion | PASS | "Start with one dbt project. Don't fire-hose." Matches scenario's dbt mention. |
| 9 | Doc citations accurate | PASS | All named sections exist in the spec. No hallucinated references. |
| 10 | Under 800 words | PASS | Body is ~770 words excluding the metadata section. |

**Score: 10/10**

Bonus items hit:
- Per-user token onboarding (step 8 mentions `/onboard`)
- Defers Slack bot to next week
- Google accounts → Clerk federation mentioned

## Notes

Strong performance. Agent compressed the 10 phases into 9 executable steps with correct ordering. Added an explicit "seed one entry" round-trip test (step 7) that isn't in the skill but is a sensible addition. Kept the cost estimate honest ($0–$25/mo). Did not hallucinate any section names.

One minor drift: recommends Drizzle for TS without being told the user is TS, but justifies it via "Vercel/Next.js shop" which is a reasonable inference.

No spec gaps surfaced by this run.
