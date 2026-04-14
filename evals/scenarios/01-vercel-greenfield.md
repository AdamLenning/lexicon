# Scenario 01: Vercel-centric startup, greenfield

## Prompt

You're my AI coding agent. I work as the solo platform engineer at a 40-person early-stage SaaS startup. We're Vercel-centric — our web app is Next.js on Vercel, our database is nothing yet (we use Supabase for our app DB but not heavily), we don't have an official SSO provider (everyone logs into internal tools with Google accounts), and we've never run Kubernetes, Docker, or any serious infra. We want to stand up lexicon so every engineer's Claude Desktop and Cursor can ground itself in our internal terminology and dbt metrics. I want a step-by-step plan I can execute this afternoon.

Read the lexicon repo at `/Users/Adam.Lenning/repos/personal/lexicon` and give me:

1. A one-paragraph summary of what lexicon is and why I need the centralized-service shape specifically
2. The storage decision (with reasoning that cites the relevant doc)
3. A numbered list of deployment steps for me to execute today
4. The specific services I'll need to sign up for
5. What I should NOT do at launch (explicitly)
6. A list of the specialist docs you consulted

Keep it under 800 words. I'm time-constrained.
