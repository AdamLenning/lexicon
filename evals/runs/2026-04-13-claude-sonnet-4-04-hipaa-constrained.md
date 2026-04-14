# Run: 04-hipaa-constrained (2026-04-13, claude-sonnet-4)

## Agent output (condensed)

### 1. Architecture recommendation

Recipe B (AWS enterprise) with two substitutions: Cognito or direct enterprise SAML instead of Clerk; Bedrock Titan embeddings (or SageMaker-hosted BGE/E5/GTE) instead of Voyage/OpenAI/Anthropic direct. All components AWS BAA-eligible: RDS PG 16 + pgvector, ECS Fargate, CloudFront+S3 or Amplify, Lambda+API Gateway (if Slack bot enabled), EventBridge, Secrets Manager, CloudWatch+X-Ray, S3 Object Lock for audit WORM, Route 53 private hosted zone, VPC PrivateLink endpoints. Internal ALB only for MCP per `AUTH.md` §Network posture.

### 2. Third-party services to avoid

Full table enumerating every default outside AWS BAA: Supabase/Neon, Fly/Railway, Vercel, Clerk/Auth0/Descope/WorkOS, Voyage AI, OpenAI, Anthropic API direct, Sentry, Honeycomb/Datadog/Tempo (verify case-by-case), Splunk (unless Splunk Cloud with BAA), Notion/Confluence/Slack/Salesforce ingestion (case-by-case based on whether source contains PHI).

### 3. Audit retention

**6 years minimum** per HIPAA 45 CFR §164.530(j)(2). Citation: `GOVERNANCE.md` §Retention "HIPAA 6 years." Implementation: 2-year hot in RDS, nightly NDJSON export to S3 with Object Lock (Compliance mode), lifecycle to Glacier Deep Archive after year 1, retain 6–7 years.

### 4. PHI avoidance

**Both filters AND policy; neither alone is sufficient.** Three layers:

**Policy:** written scope statement ("no PHI, P0 incident if violated"); narrow ingestion source allowlist (engineering Confluence ENG/INFRA/PLATFORM only; no Salesforce, no customer-ops channels); BAA signed with every touch point.

**Ingestion filters:** extend classifier prompt's PII redaction with healthtech entities (MRN, DOB, diagnosis codes, NPI, insurance IDs, ZIP3). Add **Amazon Comprehend Medical `DetectPHI` as a pre-filter BEFORE the LLM classifier** — deterministic, model-independent gate. Per-source `pii_sensitivity` gating at fetcher.

**Runtime filters:** extend `GOVERNANCE.md` §PII handling redactor with medical entities; `lexicon.propose_entry` rejects payloads that trip PHI detector with explicit error; Slack bot messages redacted before landing in proposals.

**Belt-and-suspenders:** KMS encryption, TLS, weekly batch sample of N=100 published entries run through Comprehend Medical to alarm on leakage.

### 5. Concrete embedding-architecture concern

**Embedding provider is a non-optional external dependency whose failure mode has no PHI-safe fallback, and migrations are expensive.** Citations: `DEPLOYMENT.md` `LEXICON_EMBEDDING_PROVIDER` defaults to voyage/openai/anthropic (all outside AWS BAA); `ARCHITECTURE.md` shows embeddings generated on write path after approval; `OPERATIONS.md` §Embedding-model migrations describes a 1–2 week / $50–200 re-embed. Corollary: embeddings are derived from `search_text`, and modern embedding-inversion attacks can partially reconstruct inputs — do not rely on "it's just a vector" as a PHI-safety argument.

**Mitigation:** pin `LEXICON_EMBEDDING_PROVIDER` to Bedrock Titan (or SageMaker-hosted BGE/E5/GTE behind VPC endpoint) from day one. Document in ADR that Voyage/OpenAI/Anthropic-direct are prohibited.

### 6. Does lexicon claim HIPAA compliance?

**No.** Quotes `GOVERNANCE.md` §Compliance posture: "lexicon is **not certified** — it's a specification." Spec gives building blocks (audit log, RBAC, append-only log, BAA-compatible hosting recipes, TLS/at-rest encryption) and explicitly names the defaults that would take you OUT of HIPAA scope. No "HIPAA edition."

### 7. Phased rollout

- **Phase 0 (week 0):** Security BAA prework, data-flow diagram, ADR
- **Phase 1 (week 1):** Infra + schema + audit export, hand-typed first entry, 2–3 admin onboarding
- **Phase 2 (week 2):** dbt manifest ingestion on PHI-free engineering/infra models only (structured, schema-not-rows, easily filterable). Comprehend Medical pre-filter. Curator triage. Precision ≥0.8 before advancing.
- **Phase 3 (week 3):** Engineering runbooks via file-glob, zero PHI by construction
- **Phase 4 (week 4):** Internal tool registry, hand-curated 30–100 tools; MCP client MDM push to pilot (20–50 users, platform+data teams)
- **Phase 5 (weeks 5–6):** Confluence ingestion, engineering spaces only (ENG/INFRA/PLATFORM allowlisted, not denylisted). Two-week steady-state evaluation.
- **Phase 6 (weeks 7–8):** Broader engineering rollout (~200–300 users), Slack bot in #eng-lexicon only.
- **Phase 7 (quarter 2):** Revisit non-engineering scope only if zero PHI incidents. Customer-facing/clinical indefinitely out.

Explicitly rejected: Salesforce adapter, customer/clinical Slack scraping, auto-approve.

### 8. Docs consulted

All 12 repo docs.

---EVAL METADATA---

Files read: all 12 spec files (README, ARCHITECTURE, STORAGE, DEPLOYMENT, AUTH, GOVERNANCE, INGESTION, OPERATIONS, PRIMITIVES, MCP_SPEC, CONTRIBUTION, .claude/skills/setup-lexicon.md).

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | AWS-BAA-scope architecture | PASS | Full component table with BAA-eligibility status. |
| 2 | Flags Clerk/Auth0/Descope/WorkOS | PASS | Named explicitly in "Avoid" table with reason "Outside AWS BAA." |
| 3 | Flags Voyage/OpenAI/Anthropic embedding | PASS | Named; proposes Bedrock or SageMaker-hosted alternative. |
| 4 | Flags Slack/Confluence/Salesforce adapters | PASS | Conditional — OK if source is BAA-covered or PHI-free. Salesforce banned outright. |
| 5 | Correctly says spec does NOT claim HIPAA compliance | PASS | Direct quote from `GOVERNANCE.md` §Compliance posture. |
| 6 | Audit retention ≥6 years for HIPAA | PASS | Gets the number right with CFR citation. |
| 7 | PHI avoidance: filters + policy | PASS | "Both. Neither alone is sufficient." Three layers described. |
| 8 | Concrete embedding concern | PASS | Non-optional external dependency + no PHI-safe fallback + expensive migration + embedding-inversion corollary. |
| 9 | Phased rollout lowest-risk first | PASS | dbt schemas → engineering runbooks → tool registry → engineering-only Confluence. Customer content indefinitely out. |
| 10 | BAA-covered embedding alternative | PASS | Bedrock Titan, Cohere-on-Bedrock, SageMaker-hosted BGE/E5/GTE. |
| 11 | MCP off public internet | PASS | "Never expose MCP server publicly" with AUTH.md citation. |
| 12 | Doc citations accurate | PASS | All verified. |

**Score: 12/12**

## Notes

Standout observations:
- **Amazon Comprehend Medical pre-filter** proposal — deterministic, model-independent PHI gate BEFORE the LLM classifier. Not in the spec. Professional-grade healthtech reasoning; worth considering as a spec improvement for the HIPAA path in `INGESTION.md` or a new `HIPAA.md`.
- **Embedding-inversion caveat** — "embeddings are not a one-way hash … do not rely on 'it's just a vector' as a PHI-safety argument." Sophisticated and correct.
- **"One-way door" framing on embedding provider** — honest acknowledgment that the choice is expensive to reverse.
- **Runtime MCP query redaction** — even if a user types PHI into their Claude query, the audit log should redact. Subtle catch from `GOVERNANCE.md` §PII handling.
- **Confluence allowlist not denylist** — correct security posture. Allowlists fail closed.
- **Weekly PHI-leakage audit via sampling** — belt-and-suspenders.
- **Rejects Salesforce adapter entirely** — correct for a healthtech where Salesforce contains customer PHI.

## Spec gap identified

The agent produced an excellent HIPAA implementation plan from the spec, but it *synthesized* several HIPAA-specific enhancements (Comprehend Medical pre-filter, medical-entity extension to PII redactor, embedding-inversion caveat) that aren't explicitly in the spec. Consider adding a `COMPLIANCE.md` or expanding `GOVERNANCE.md` §Compliance posture with HIPAA-specific patterns so that the next agent doesn't have to re-derive them. The spec succeeds here — but it's leaning on the agent's knowledge, not the spec's guidance.
