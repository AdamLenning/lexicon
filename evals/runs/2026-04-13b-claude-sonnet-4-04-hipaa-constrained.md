# Re-run: 04-hipaa-constrained (2026-04-13 post-gap-fixes, claude-sonnet-4)

## Agent output (summary)

Same conclusions as first run (architecture, tools to avoid, retention, PHI-avoidance strategy, embedding concern, no HIPAA certification claim, phased rollout). But the SOURCES are now different:

**First run:** agent synthesized HIPAA-specific patterns (Comprehend Medical, medical-entity PII extension, Bedrock as default, embedding-inversion caveat, 7-phase rollout) from general knowledge plus the spec's hooks.

**Re-run:** agent sources every HIPAA-specific pattern from COMPLIANCE.md. Quotes verbatim:
- *"embeddings are not one-way hashes. Modern inversion attacks can partially reconstruct input text from vectors. Your vector column is sensitive. Don't rely on 'it's just a vector' as a PHI-safety argument."*
- *"No single layer is sufficient. Build all five"* (the defense-in-depth framing)
- The exact 8-phase rollout (Phases 0–7) is quoted as spec content
- BAA matrix cited as a source table
- *"There is no 'HIPAA edition' or 'SOC 2 edition'"*

Agent names COMPLIANCE.md as the **primary** doc: *"COMPLIANCE.md (primary — the HIPAA section answered most of the brief directly)."*

## Grading

| # | Dimension | Pass/Fail | Notes |
|---|-----------|-----------|-------|
| 1 | AWS-BAA-scope architecture | PASS | Full component table; Bedrock embedding default explicit. |
| 2 | Flags Clerk/Auth0/Descope/WorkOS | PASS | Table row citing COMPLIANCE.md BAA matrix. |
| 3 | Flags Voyage/OpenAI/Anthropic embedding | PASS | Separate rows in avoid table, each citing COMPLIANCE.md. |
| 4 | Flags Slack/Confluence/Salesforce adapters | PASS | Uses COMPLIANCE.md source-scoping table. |
| 5 | Correctly says not HIPAA certified | PASS | Quotes COMPLIANCE.md opening and disclaimer. |
| 6 | Audit retention ≥6 years | PASS | Cites COMPLIANCE.md §HIPAA → "Audit retention specific to HIPAA." |
| 7 | PHI avoidance: filters + policy | PASS | **Upgraded:** now cites COMPLIANCE.md §"Defense in depth (five layers)" as canonical source; previously synthesized. |
| 8 | Concrete embedding concern | PASS | **Upgraded:** embedding-inversion caveat quoted verbatim from COMPLIANCE.md; previously agent-synthesized. |
| 9 | Phased rollout lowest-risk first | PASS | **Upgraded:** 8-phase plan quoted from COMPLIANCE.md §"Phased rollout (healthtech-specific)"; previously agent-synthesized. |
| 10 | BAA-covered embedding alternative | PASS | **Upgraded:** Bedrock Titan / Cohere-on-Bedrock / SageMaker now cited from spec rather than synthesized. |
| 11 | MCP off public internet | PASS | Cited from AUTH.md. |
| 12 | Doc citations accurate | PASS | All verified. |

**Score: 12/12**

Spec gap #1 (COMPLIANCE.md) **decisively closed.** Previously-synthesized HIPAA patterns are now durable spec content. Any model with weaker HIPAA knowledge than Claude Sonnet will now produce the same answer because the patterns are in the spec, not the agent.

The response is tighter than the first run in terms of justification quality — the agent spends fewer cycles reasoning from first principles and more cycles applying the spec.
