# Re-run: 02-aws-existing-postgres (2026-04-13 post-gap-fixes, claude-sonnet-4)

## Agent output (summary)

Same storage (dedicated new RDS PG16 + pgvector), same compute (ECS Fargate), same auth (Okta SAML direct), same 6 security-review items. Plus:

- **NEW:** Reads COMPLIANCE.md (it didn't exist in the first run). Agent read all 13 repo files.
- **NEW:** Security-review item #1 now uses verbatim quoted language from the updated AUTH.md bootstrap-admin callout: *"The first user to complete SSO becomes admin by default — this is a real privilege-escalation footgun if left unguarded."*
- **NEW:** Security-review item #3 (audit retention) quotes COMPLIANCE.md §SOC 2 Type II directly: *"Retention ≥1 year (audit minimum; longer is safer)"* and lists "Audit retention too short (auditor wants ≥1 year; default to 2+)" from the new §"Common SOC 2 stumbling blocks."
- **NEW:** Security-review item #2 (embedding provider) pulls the embedding-inversion caveat from COMPLIANCE.md §HIPAA even though scenario isn't HIPAA — cross-framework application is correct.
- **NEW:** Phase 1 notes FTS-only degradation path ("lexicon.search still returns results via FTS-only") as an acceptable state if security hasn't approved embeddings. Pulled from OPERATIONS.md §"Embedding provider outage" — was referenced in first run too, but now integrated with COMPLIANCE.md as a deferral strategy.

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | Storage: pgvector on RDS | PASS | Dedicated new RDS recommended. |
| 2 | Does NOT suggest Supabase/Fly/Vercel | PASS | Explicit compliance with constraint. |
| 3 | Compute: ECS Fargate | PASS | MCP+REST + ingestion on Fargate. |
| 4 | Auth: Okta SAML direct | PASS | "Direct SAML federation with Okta, no third-party IdP proxy." |
| 5 | VPC isolation | PASS | Private subnets, VPC endpoints, SG allowlist. |
| 6 | ≥3 security-review items | PASS | 6 items. |
| 7 | Each item cites right doc | PASS | Verified. |
| 8 | SOC 2-aware posture | PASS | **Upgraded:** now quotes COMPLIANCE.md §SOC 2 directly (new spec content); previously synthesized. |
| 9 | Phase 1 vs Phase 2 split | PASS | Adds embedding-deferred FTS-only operation as P1 fallback. |
| 10 | Backup/PITR mentioned | PASS | KMS CMK + Multi-AZ + PITR ≥30d. |
| 11 | No auto-publish | PASS | Quotes "requires 3+ months of ≥0.9 precision first." |
| 12 | Doc citations accurate | PASS | All verified. |

**Score: 12/12**

Spec gap #1 (COMPLIANCE.md) verified: agent reads it and quotes §SOC 2 Type II directly for a SOC 2 scenario.

Spec gap #3 (bootstrap-admin explicit) verified: agent quotes the new AUTH.md callout language in security item #1.
