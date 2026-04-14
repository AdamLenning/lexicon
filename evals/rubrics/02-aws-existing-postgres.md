# Rubric 02: AWS enterprise with existing Postgres

Each dimension is pass/fail worth 1 point. Total: 12 points.

## Dimensions

1. **Storage: add pgvector to existing RDS (or separate RDS)** — Agent picks RDS PostgreSQL + pgvector per `STORAGE.md` matrix row "AWS-only enterprise" / "Postgres already running." Either extending an existing RDS or standing up a dedicated RDS instance is acceptable; dedicated is slightly preferred for isolation.

2. **Does NOT suggest Supabase/Neon/Fly/Vercel** — Scenario explicitly rules these out. Any mention as a recommendation is a fail. (Mentioning them as alternatives that were ruled out is acceptable.)

3. **Compute: ECS Fargate for MCP+REST** — Per `DEPLOYMENT.md` §Recipe B (AWS enterprise). App Runner is an acceptable substitute.

4. **Auth: Okta via SAML (OIDC wrapper)** — Agent integrates with the company's Okta directly rather than adding Clerk/Auth0. Per `AUTH.md` §Provider recommendations row "Company SSO (Okta/Entra/Google)."

5. **VPC isolation mentioned** — Agent places everything in the VPC per the scenario's network constraints and `DEPLOYMENT.md`'s AWS recipe.

6. **≥3 security-review items surfaced** — Agent lists at least 3 security concerns that warrant review. Expected candidates:
   - Per-user MCP tokens vs existing IdP session model (from `AUTH.md`)
   - Embedding API (Voyage/OpenAI) is a third-party data egress path (from `DEPLOYMENT.md` env vars + `OPERATIONS.md`)
   - Audit log retention vs SOC 2 requirements (from `GOVERNANCE.md`)
   - PII redaction in audit log args (from `GOVERNANCE.md`)
   - SIEM integration (from `GOVERNANCE.md` + `OPERATIONS.md`)
   - Network posture: MCP server internal-only DNS (from `AUTH.md`)

7. **Each security item cites the right doc** — The doc the agent names actually covers the issue.

8. **SOC 2-aware posture** — Agent notes `GOVERNANCE.md` §Compliance posture and says lexicon has hooks for SOC 2 (audit log, RBAC, access reviews) but isn't certified itself.

9. **Phase 1 vs Phase 2 split is sensible** — Core service + auth + audit in Phase 1. Ingestion adapters, Slack bot, aggressive scraping in Phase 2 (post security-sign-off). Not required to match exactly but the split should reflect "security-review-blocking-items first."

10. **Mentions backup/PITR for RDS** — Per `OPERATIONS.md` §Backups. Shows the agent is thinking enterprise-ops.

11. **Correctly doesn't auto-publish ingested entries** — Respects the non-negotiable per `GOVERNANCE.md` §Approval workflow.

12. **Doc citations accurate** — Doesn't invent section names; cites real docs and real sections.

## Failure modes to watch for

- Proposes Supabase/Vercel despite the scenario forbidding them
- Skips the security-review asks (the user explicitly requested them)
- Claims SOC 2 certification ("lexicon is SOC 2 compliant") — spec says it has hooks, not certification
- Puts audit log retention too low (<1 year for SOC 2)
- Suggests binding MCP server to public internet with only token auth as defense
