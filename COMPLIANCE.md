# Compliance

Per-framework implementation patterns for deploying `lexicon` in regulated environments. The spec itself is not certified — this doc tells you how to implement the spec in a way that satisfies your auditor.

**Important:** deploying under a compliance framework is your organization's responsibility, not the spec's. This doc names the patterns that fit, the hooks the spec provides, and the common mistakes that fail review. Your security and legal teams own the certification decisions.

## Reminder: lexicon is a specification, not a certified product

From [`GOVERNANCE.md`](./GOVERNANCE.md) §Compliance posture, repeated here because it matters:

> lexicon is **not certified** — it's a specification. A company pursuing certification implements this spec in a way that satisfies its auditor. The spec does not include the auditor.

Everything below is about *implementing* this spec to fit your framework. There is no "HIPAA edition" or "SOC 2 edition" — there's your deployment, and the patterns to follow.

---

## HIPAA (US healthtech with PHI)

Applies when: your org handles Protected Health Information and has signed BAAs with your cloud and vendors. Typical use for lexicon: internal engineering + data teams grounding their agents in non-PHI organizational context (data warehouse schemas, engineering runbooks, internal tool registry). **Not** patient-facing.

### Key requirements from HIPAA
- Audit log retention ≥ 6 years (45 CFR §164.530(j)(2))
- BAA-covered hosting for any service that touches PHI-adjacent data
- Encryption at rest + in transit
- Access controls, audit logs, integrity controls, transmission security (§164.312)
- PHI must never enter the store — this is policy, not just technology

### Implementation pattern

#### Storage + compute (stay inside your cloud's BAA scope)

For AWS (most common healthtech posture):

| Component | Service | BAA |
|---|---|---|
| Storage | RDS PostgreSQL 16 + pgvector, KMS CMK, automated backups, Multi-AZ | Yes |
| Compute | ECS Fargate or App Runner behind internal ALB | Yes |
| Web UI | CloudFront + S3, or Amplify, SSO-gated | Yes |
| Slack bot (if enabled) | Lambda + API Gateway | Yes |
| Ingestion workers | EventBridge + Lambda, or ECS scheduled tasks | Yes |
| Secrets | AWS Secrets Manager with rotation | Yes |
| Logs + metrics + traces | CloudWatch Logs + Metrics + X-Ray | Yes |
| Audit-log cold tier | S3 with Object Lock (Compliance mode) + Glacier lifecycle | Yes |
| Identity | Cognito, or direct enterprise SAML (Okta/Entra with BAA) | Yes (Cognito) / varies (IdP) |
| DNS | Route 53 private hosted zone (`lexicon-mcp.company.internal`) | Yes |

All traffic between these components stays inside your VPC via PrivateLink endpoints. Never expose the MCP server publicly.

#### Embedding provider (the critical choice)

This is where most HIPAA deployments fail without realizing it.

**Use:**
- **Amazon Bedrock** — Titan embeddings or Cohere on Bedrock. BAA-covered end-to-end on AWS.
- **SageMaker-hosted model** — self-host `BGE-large`, `E5-large`, or `GTE-large` behind a VPC endpoint. Fully inside your account.

**Do NOT use (outside AWS BAA by default):**
- Voyage AI
- OpenAI (even "enterprise" — confirm BAA specifically before relying on it)
- Anthropic direct API (use Anthropic on Bedrock instead)

**Embedding-inversion caveat:** embeddings are *not* one-way hashes. Modern inversion attacks can partially reconstruct input text from vectors. Your vector column is sensitive. Don't rely on "it's just a vector" as a PHI-safety argument.

**Migration cost:** per [`OPERATIONS.md`](./OPERATIONS.md) §Embedding-model migrations, swapping providers is 1–2 engineer-weeks and $50–200 in API costs, plus a corpus re-embed. Treat the choice as a one-way door; document it in an ADR; don't drift.

Set `LEXICON_EMBEDDING_PROVIDER=bedrock` (or your self-hosted alias) from day one. Lock it in your infra code.

#### PHI-avoidance: defense in depth (five layers)

No single layer is sufficient. Build all five.

**Layer 1 — Policy.** A written scope statement: "lexicon stores engineering + data-platform context only. It does NOT accept clinical, claims, eligibility, or patient-identifying content. PHI ingestion is a P0 incident." Publish in the runbook; reference on every onboarding.

**Layer 2 — Narrow source allowlist (not denylist).** Allowlists fail closed. Allow: engineering Confluence/Notion spaces, dbt manifests for non-clinical schemas, internal tool registry, engineering runbooks. Deny: Salesforce, customer-ops Slack channels, clinical wikis, HIE-facing systems.

**Layer 3 — Deterministic pre-filter.** Before the LLM classifier sees any content, run it through **Amazon Comprehend Medical `DetectPHI`**. Any chunk with PHI entities above threshold gets dropped at the fetcher. This is a model-independent gate you can point at in an audit.

**Layer 4 — LLM classifier hardening.** Extend the classifier prompt (per [`INGESTION.md`](./INGESTION.md) §"What not to ingest") with healthtech-specific entities: MRN, DOB, dates of service, diagnosis codes, NPI numbers, insurance IDs, addresses to ZIP3. Explicit instruction to return an empty proposal list when PHI is detected.

**Layer 5 — Runtime + audit redaction.** Per [`GOVERNANCE.md`](./GOVERNANCE.md) §PII handling in args, the audit redactor handles email/phone/SSN/address. Extend it with medical entities so a user query containing PHI (e.g., *"tell me about patient John Smith's MRN 1234567"*) persists with `args` redacted but attribution intact. Additionally, have `lexicon.propose_entry` server-side reject any payload that trips the PHI detector with an explicit error (*"PHI detected; submit through your approved workflow"*).

**Belt-and-suspenders.** A weekly batch job samples N=100 published entries, runs Comprehend Medical, and alarms on any hit. Catches what slipped past layers 3–4.

#### Ingestion source scoping

| Source | Posture | Why |
|---|---|---|
| File-glob (internal markdown) | Allow (scoped) | Engineering content only; verify paths |
| dbt manifest | Allow (scoped) | Schema metadata, not rows; exclude clinical-schema models |
| Engineering Confluence (ENG / INFRA / PLATFORM spaces) | Allow (allowlist by space-key) | Engineering content only |
| Notion engineering workspace | Allow (scoped to specific parent pages) | Same |
| Customer-facing Confluence / Notion | **Deny** | Risk of PHI |
| Slack — engineering channels (`#eng-*`, `#data-*`) | Allow with filters | Still run pre-filter + classifier |
| Slack — customer-ops / care-team channels | **Deny** | High PHI risk |
| Salesforce | **Deny** | Customer records almost certainly contain PHI |
| HIE / EMR integrations | **Deny** | Never |

#### BAA matrix for common third-party services

Verify current status with your security + legal teams; vendor BAA availability changes. Assume "No" until confirmed.

| Service | BAA available? (as of 2026) | Recommendation |
|---|---|---|
| AWS (RDS, ECS, Bedrock, Cognito, S3, CloudWatch, PrivateLink) | Yes, broad | Use by default |
| Anthropic on Bedrock | Yes | Preferred LLM path |
| Anthropic direct API | Enterprise tier, case-by-case | Don't rely on it; route through Bedrock |
| OpenAI | Enterprise, limited | Avoid; route through Bedrock alternatives |
| Voyage AI | No | Do not use for HIPAA |
| Cohere on Bedrock | Yes | Good embedding option |
| Clerk / Auth0 / Descope / WorkOS | Varies; default assume No | Use Cognito or direct enterprise SAML |
| Datadog | Yes on HIPAA tier | Verify your contract |
| Sentry | No (as of 2026) | Use CloudWatch + X-Ray |
| Splunk Cloud | Yes | Verify your contract |
| Honeycomb / Grafana Tempo | Varies | Verify; default to CloudWatch if uncertain |
| Notion / Confluence / Slack / Salesforce | Source-dependent | Source must be in BAA scope OR contain no PHI |

#### Phased rollout (healthtech-specific)

Tighter than the default rollout in [`DEPLOYMENT.md`](./DEPLOYMENT.md) §Rollout sequence.

- **Phase 0 (week 0):** Security + legal sign-off on data-flow diagram + scope statement. Confirm BAA coverage. Write ADR locking in storage, compute, embedding, and identity picks.
- **Phase 1 (week 1):** Infra only — VPC, RDS + pgvector, ECS, KMS, Secrets Manager, Cognito/SAML, CloudWatch, S3 Object Lock audit bucket. Primitive schemas + `*_versions` + `audit_log`. One hand-typed test entry. 2–3 platform engineers as admins.
- **Phase 2 (week 2):** Ingestion on dbt manifest only, scoped to engineering/infra schemas with `pii_sensitivity: none`. Comprehend Medical pre-filter enabled. Curator triage of first 20–50 proposals together. Precision ≥ 0.8 to advance.
- **Phase 3 (week 3):** Ingestion on engineering runbooks (file-glob over internal-only markdown). Same pre-filter. Curator triage.
- **Phase 4 (week 4):** Hand-curate 30–100 internal tool registry entries via REST. MDM push of MCP client config to pilot users (platform + data teams, ~20–50 people).
- **Phase 5 (weeks 5–6):** Confluence on ENG/INFRA/PLATFORM space allowlist only. Two-week steady-state evaluation; review audit-sample job results.
- **Phase 6 (weeks 7–8):** Broader engineering rollout (~200–300 users of a 600-person company). Slack bot enabled in engineering channels only.
- **Phase 7 (Q2+):** Revisit non-engineering scope only if audit shows zero PHI incidents. Customer-facing / clinical content remains out indefinitely without a separate, purpose-built PHI-permitted instance.

#### Explicit anti-patterns for HIPAA deployments

- Auto-approve on any ingestion source (ever, for this framework)
- Embedding with non-BAA providers
- Shared admin tokens
- Customer-facing, support, or clinical content in this lexicon instance
- MCP server on public DNS
- Denylist-style filtering ("block anything matching PHI patterns") — allowlist instead
- Relying on "it's just a vector" as PHI safety

#### Audit retention specific to HIPAA

Per [`GOVERNANCE.md`](./GOVERNANCE.md) §Audit log retention: **≥6 years** (regulatory minimum under 45 CFR §164.530(j)(2)). Recommend 7 years to align with most state-specific HIE rules and BAA terms. Architecture:

- 2 years hot in RDS
- Nightly NDJSON export to S3 with Object Lock (Compliance mode)
- Lifecycle transition to Glacier Deep Archive after year 1
- Total retention ≥7 years
- Ship same NDJSON to your SIEM (Splunk Cloud on HIPAA tier, Datadog on HIPAA tier, or equivalent)

---

## SOC 2 Type II

Applies when: your org is pursuing or maintains SOC 2 Type II certification. lexicon's governance primitives give you hooks for most Trust Service Criteria.

### Pattern

- **Audit log** — [`GOVERNANCE.md`](./GOVERNANCE.md) §Audit log gives you per-request attribution. For SOC 2, ensure:
  - Retention ≥1 year (audit minimum; longer is safer)
  - Immutable / append-only storage (S3 Object Lock or equivalent)
  - SIEM export configured and verified with a weekly synthetic event
  - PII redactor documented and tested
- **RBAC** — the reader/curator/admin roles satisfy least-privilege. Access reviews per [`OPERATIONS.md`](./OPERATIONS.md) §Quarterly satisfy CC6.2. Document:
  - List of all curators and admins (current state)
  - Evidence of quarterly access review (confirmation emails, tickets, or similar)
  - Role promotion/demotion history (from audit log)
- **Change management** — migrations, deployments, and config changes must be PR-reviewed + CI-tested + audit-logged. The `*_versions` tables per [`GOVERNANCE.md`](./GOVERNANCE.md) §Version history satisfy change-tracking on content.
- **Encryption** — at-rest via provider KMS, in-transit via TLS. Standard.
- **Incident response** — [`OPERATIONS.md`](./OPERATIONS.md) §Incident playbook covers the common scenarios. Adopt; tailor; rehearse.
- **Availability** — the 99.9% target in [`ARCHITECTURE.md`](./ARCHITECTURE.md) §Non-functional requirements is a stretch goal. For a real SOC 2 availability commitment, adopt multi-region RDS + MCP server replicas, and monitor with synthetic checks.
- **Vendor management** — maintain the vendor list (hosting, identity, embedding, observability) with DPAs / sub-processor agreements as required.

### Common SOC 2 stumbling blocks

- Audit retention too short (auditor wants ≥1 year; default to 2+)
- No documented PII redactor tests — write them
- Admin role changes not logged with justification — the spec logs the change; document the justification as a required comment
- Vendor sub-processors not tracked — especially for embedding and LLM providers

---

## GDPR (EU data subjects)

Applies when: your lexicon users or ingested content contain personal data of EU residents.

### Pattern

- **Data locality.** Host Postgres and compute in an EU region (Supabase EU, Neon EU region, RDS `eu-west-1` / `eu-central-1`, Cloud SQL `europe-*`). Embedding provider must be configured for EU endpoint or self-hosted in an EU region.
- **Audit retention.** Per [`GOVERNANCE.md`](./GOVERNANCE.md) §Retention, 2 years hot / 5 years cold is conservative. For GDPR, ensure no retention beyond legitimate business need; document the retention justification in a records-of-processing log.
- **Right to erasure.** When a user is deactivated (SSO deprovision per [`AUTH.md`](./AUTH.md) §Offboarding), their `user_id` is retained in audit logs for integrity but should be pseudonymized on request. Add a `GET /users/:id/erasure` admin endpoint that:
  1. Replaces `user_id` in audit logs with a stable pseudonym (`erased-user-<hash>`)
  2. Reassigns ownership of any `owner = :user_id` entries to a team account
  3. Logs the erasure event itself
- **Data subject access.** For SARs, an admin endpoint returns the audit log rows attributed to a given user and the entries they created/edited.
- **DPIA prompts.** Ingesting Slack/Confluence content may pull personal data (author names, mentioned colleagues, customer comments). The classifier's PII redaction helps but is not a DPIA substitute. Document the ingestion sources, categories of personal data processed, lawful basis, and retention for each.
- **Sub-processor list.** Embedding providers, LLM providers, hosting, identity, and SIEM each need to appear on your sub-processor list with a signed DPA.

### Common GDPR stumbling blocks

- Hosting in a US region by default — check your Supabase/Neon/RDS region on day one
- Non-EU embedding provider — use EU-hosted alternative or self-host
- Not distinguishing audit-log identity retention (legitimate interest) from user data retention (data minimization)

---

## Frameworks not yet covered

If your framework isn't here, the spec's governance primitives probably support it — but document the pattern so others benefit.

- **PCI-DSS:** generally wrong fit for lexicon (cardholder context shouldn't live in a shared knowledge store). If you have a specific reason, open an issue.
- **FedRAMP / IL-series:** achievable on AWS GovCloud + matching compute; requires BAA-equivalent sub-processor discipline. Out of scope for this spec; contact a FedRAMP consultant.
- **ISO 27001 / 27017 / 27018:** overlaps heavily with SOC 2 controls. Use the SOC 2 pattern as a starting point.

## Adding a new framework pattern

1. Name the framework and who it applies to
2. Enumerate the spec hooks that satisfy it (audit log, RBAC, retention, encryption, access reviews)
3. Name the common stumbling blocks
4. Open a PR; explain what changed for future auditors

## Disclaimer (read this)

This doc is a **specification pattern**, not legal, security, or compliance advice. Engage your auditors, lawyers, and security teams before relying on any of the above for a real certification. Regulations change; vendor BAA availability changes; this doc drifts. Always verify current status directly with your vendors and your auditor.
