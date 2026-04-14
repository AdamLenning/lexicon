# Rubric 04: HIPAA-covered healthtech

Each dimension is pass/fail worth 1 point. Total: 12 points.

## Dimensions

1. **AWS-BAA-scope architecture** — Per `DEPLOYMENT.md` §Recipe B: RDS PostgreSQL + ECS/App Runner + VPC isolation. All AWS services that are BAA-covered.

2. **Flags Clerk (and other third-party OIDC) as potential BAA gap** — Per `AUTH.md` §Provider recommendations, Clerk / Auth0 / Descope are called out as default choices. Agent correctly notes that using them requires a separate BAA (or avoiding them entirely in favor of Okta/Entra with a BAA or direct AWS Cognito).

3. **Flags Voyage/Anthropic/OpenAI embedding APIs** — Per `DEPLOYMENT.md` env vars + `INGESTION.md`. These are third-party data egress; agent asks whether BAAs exist. (As of 2025-2026, Anthropic has BAA availability on enterprise tier; Voyage/OpenAI status varies — agent doesn't need to know the specifics but must flag the concern.)

4. **Flags Slack/Confluence/Salesforce ingestion adapters** — These all involve pulling content that could contain PHI. Must be configured carefully per `INGESTION.md` §"What not to ingest."

5. **Correctly states spec does NOT claim HIPAA compliance** — Per `GOVERNANCE.md` §Compliance posture: "lexicon is not certified — it's a specification." Agent honest about this. Getting this wrong (claiming compliance) is a significant fail.

6. **Audit retention ≥6 years for HIPAA** — Per `GOVERNANCE.md` §Audit log retention which says "HIPAA 6 years." Agent gets the number right.

7. **PHI-avoidance strategy: ingestion filters + policy** — Per `INGESTION.md` §"What not to ingest," classifier prompt already has a PII redaction instruction. Agent cites it. Also mentions organizational policy prohibiting PHI in lexicon entries is needed — can't just rely on automation.

8. **Names at least one concrete embedding-architecture concern** — Expected candidates: third-party API egress, data locality (if provider doesn't offer US region), retention in the provider's cache, inference input logging by provider. Any reasonable concern scores.

9. **Phased rollout: starts with lowest-risk data** — Engineering runbooks, dbt schemas, internal tool registry — all fine. Customer-facing content, support tickets, patient-adjacent content — later or never. Per `INGESTION.md` §Bootstrap strategy.

10. **Proposes BAA-covered embedding alternative** — Options include: (a) use Anthropic's BAA-covered embedding access on enterprise tier, (b) self-host an embedding model (BGE, sentence-transformers) behind the VPC, (c) Bedrock-hosted embedding models (Titan, Cohere via Bedrock) which are BAA-covered on AWS. Partial credit for naming any one of these.

11. **Keeps MCP server off public internet** — Per `AUTH.md` §Network posture: internal DNS only. Important for HIPAA defense-in-depth.

12. **Doc citations accurate** — No invented sections, no misattributed compliance claims.

## Failure modes to watch for

- Claims lexicon "is HIPAA compliant" (spec does not)
- Misses the third-party embedding API egress concern
- Recommends Supabase or Vercel for HIPAA deployment (not in AWS BAA scope by default)
- Too-low audit retention (<6 years)
- Waves hands at PHI avoidance without citing the ingestion filter mechanism
- Treats Clerk/Auth0 as fine without flagging the BAA question
