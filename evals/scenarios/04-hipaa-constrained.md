# Scenario 04: HIPAA-covered healthtech

## Prompt

I'm the head of engineering at a 600-person US-based healthtech company. We handle PHI for hospital customers; we're fully HIPAA-covered, have a signed BAA with AWS, and our security team is paranoid (rightly). We're interested in lexicon for our internal engineering + data teams — NOT patient-facing. Context entries would cover our data warehouse schemas, engineering runbooks, internal tool registry. No PHI should enter lexicon itself.

Please design a HIPAA-safe deployment. I need:

1. Architecture recommendation that stays inside our AWS BAA scope
2. What tooling/third-party services we should AVOID that the default recipes use (with the doc that mentions them)
3. Audit log retention target (and where the doc is)
4. How we keep PHI from leaking into lexicon (ingestion filters? Policy? Both?)
5. One concrete concern about the embedding provider architecture in the spec
6. Whether lexicon claims HIPAA compliance (be honest about what the spec says)
7. A phased rollout that starts with lowest-risk engineering data first
8. Docs consulted

Repo: `/Users/Adam.Lenning/repos/personal/lexicon`.
