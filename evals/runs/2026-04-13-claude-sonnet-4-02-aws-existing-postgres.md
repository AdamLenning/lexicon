# Run: 02-aws-existing-postgres (2026-04-13, claude-sonnet-4)

## Agent output

### 1. Storage decision

Use an existing RDS PostgreSQL 16 instance (or a new one from the same pattern) with the `pgvector` extension enabled in a dedicated `lexicon` database.

Cited `STORAGE.md` §Decision matrix rows ("AWS-only enterprise" and "Postgres already running"). Noted 50MB–200MB dataset size (§Scale assumption). Recommended new dedicated `db.t4g.small` over piggybacking on existing prod for blast-radius isolation. Confirmed pgvector on RDS PG 15+.

### 2. Deployment architecture

- **Storage:** RDS PG 16 in private subnets, Multi-AZ, KMS CMK, PITR 30 days (per `OPERATIONS.md` §Backups). Schema per `PRIMITIVES.md` + `audit_log` per `GOVERNANCE.md`. Indexes: B-tree/GIN/IVFFlat. Secrets Manager with rotation.
- **Compute:** ECS Fargate service for MCP+REST combined (single container), 0.5 vCPU / 1GB, 2 tasks behind internal ALB. ECS Fargate service for Web UI (not Vercel). Ingestion as scheduled ECS tasks via EventBridge, not Lambda. ECR, existing CI/CD.
- **Auth:** Okta SAML directly per `AUTH.md` §Provider recommendations — "skip the third-party, integrate direct." Per-user JWT tokens, 90-day expiry, revocation list. SCIM deprovisioning hook.
- **Network:** All in VPC private subnets. Internal ALB only (`lexicon-mcp.company.internal`). Internal-only Web UI by default. VPC endpoints for ECR/Secrets Manager/S3/CloudWatch. Embedding API through NAT/egress proxy. CloudWatch + OTel.

### 3. Security-review items to flag (6 items)

1. **Outbound embedding API calls send company content off-AWS.** Cites `DEPLOYMENT.md`. Options: vendor-list provider with DPA, Bedrock Titan/Cohere, or self-hosted via SageMaker.
2. **LLM-driven ingestion is a prompt-injection and data-exfil surface.** Cites `INGESTION.md` §"What not to ingest." Requires classifier log redaction, prompt-injection test cases, review-queue audit.
3. **MCP server must not be publicly exposed even with per-user tokens.** Cites `AUTH.md` §Network posture and `DEPLOYMENT.md` §DNS/TLS. Validate VPN/ZeroTrust path.
4. **Audit log retention, SIEM export, PII redaction for SOC 2 Type II.** Cites `GOVERNANCE.md` §Retention, §Export to SIEM, §PII handling + `OPERATIONS.md` §Quarterly access reviews. WORM S3, documented redactor tests.
5. **Bootstrap admin "first login wins" footgun.** Cites `AUTH.md` §RBAC. Mitigation: restrict Okta SAML app assignment to a single platform engineer for first deploy.
6. **Direct DB writes bypass audit + version history.** Cites `GOVERNANCE.md` §Anti-patterns. Break-glass DBA procedures, trigger-level guards from day one.

### 4. Phase 1 vs Phase 2

**Phase 1:** RDS + pgvector, full schema + audit infra, MCP+REST on ECS, internal-only ALB, Okta SAML → JWT, audit log + PII redactor + SIEM export, agent-assisted MCP writes (review-queue gated), manual seed of 20–100 entries, 3–10 user pilot.

**Phase 2:** embedding provider post-security-selection (lexical-only search in meantime — `OPERATIONS.md` confirms graceful degradation), ingestion scrapers (dbt first, lowest injection surface), Slack bot, public Web UI, auto-approve thresholds (only after 3 months ≥0.9 precision), HNSW swap (>100K vectors), MCP gateway strategy (currently self-service onboarding), read replicas (not needed at launch).

### 5. Docs consulted

All 12 repo docs: README, ARCHITECTURE, STORAGE, DEPLOYMENT, AUTH, GOVERNANCE, INGESTION, OPERATIONS, PRIMITIVES, MCP_SPEC, CONTRIBUTION, .claude/skills/setup-lexicon.

---EVAL METADATA---

Files read:
- README.md, ARCHITECTURE.md, STORAGE.md, DEPLOYMENT.md, AUTH.md, GOVERNANCE.md, INGESTION.md, OPERATIONS.md, PRIMITIVES.md, MCP_SPEC.md, CONTRIBUTION.md, .claude/skills/setup-lexicon.md

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | Storage: pgvector on RDS (or separate RDS) | PASS | Dedicated new RDS recommended with blast-radius reasoning. |
| 2 | Does NOT suggest Supabase/Vercel/Fly | PASS | Explicitly respects the constraint; even says "do **not** use Vercel per your constraint." |
| 3 | Compute: ECS Fargate | PASS | MCP+REST as single container, Web UI and ingestion also ECS. |
| 4 | Auth: Okta SAML direct | PASS | Quotes `AUTH.md` line verbatim on skipping third-party. |
| 5 | VPC isolation | PASS | Private subnets, VPC endpoints, internal ALBs. |
| 6 | ≥3 security-review items | PASS | Surfaces 6 items. Exceeds threshold comfortably. |
| 7 | Each item cites the right doc | PASS | Every citation is accurate. |
| 8 | SOC 2-aware posture | PASS | Item #4 names SOC 2 evidence plan, WORM S3, quarterly access reviews. |
| 9 | Phase 1 vs Phase 2 split sensible | PASS | Core + auth + audit in P1; scrapers, embedding provider, Slack, public UI in P2. Defers per security-review-blocking. |
| 10 | Backup/PITR mentioned | PASS | "PITR 30 days, Multi-AZ" with `OPERATIONS.md` cite. |
| 11 | No auto-publish | PASS | "review-queue gated, no auto-publish." |
| 12 | Doc citations accurate | PASS | All section names verified to exist. |

**Score: 12/12**

## Notes

Exceptional response. Six security-review items (threshold was three), with three especially sharp observations:

1. **Bootstrap admin "first-login-wins" footgun** — this is real spec guidance buried in `AUTH.md` §RBAC. Surfacing it as a SOC 2-critical gap is excellent reasoning.
2. **Lexical-only degradation when embedding provider is unavailable** — cited `OPERATIONS.md` to propose running without embeddings during security review. Shows deep spec understanding.
3. **Prompt-injection surface on ingestion** — caught the subtle risk from `INGESTION.md` §"What not to ingest" that humans might otherwise miss.

Agent read all 12 spec docs (100% coverage) before answering. Citations all verified accurate.

No spec gaps surfaced. If anything this run suggests the spec has enough nuance to support sophisticated enterprise reasoning.
