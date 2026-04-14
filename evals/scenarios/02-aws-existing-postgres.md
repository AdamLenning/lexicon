# Scenario 02: AWS enterprise with existing Postgres

## Prompt

I lead platform engineering at a 1200-person B2B SaaS company. We're AWS-only — every service runs in our VPC, we use RDS PostgreSQL 16 extensively (we have five production RDS instances right now), our SSO is Okta with SAML, compute is mostly ECS Fargate with some EKS. We have a dedicated security team that will review anything new, and we're mid-pursuit of SOC 2 Type II.

We want to add lexicon as a company service. Please propose a deployment plan that fits our existing patterns — do NOT propose third-party managed databases or Vercel-style hosting, they won't pass security review. Also flag anything in the lexicon spec that I should raise with our security team before implementing.

Response format:
1. Storage decision (with doc citation)
2. Deployment architecture (storage, compute, auth, network)
3. Security-review items I need to flag (≥3 items, with the doc each comes from)
4. What we'll defer to Phase 2 (after security sign-off) vs do in Phase 1
5. Docs you consulted

Read only the repo at `/Users/Adam.Lenning/repos/personal/lexicon`.
