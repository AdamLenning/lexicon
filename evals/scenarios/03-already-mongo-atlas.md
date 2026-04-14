# Scenario 03: Already running Mongo Atlas

## Prompt

Hi! I'm the tech lead at a 300-person e-commerce company. Our entire backend runs on Mongo Atlas — we've been on Atlas for 5 years, our team has deep Mongo expertise, and the idea of standing up a Postgres just for the Context Store makes our ops engineer grumpy. We don't have Postgres anywhere in production.

Can we still use lexicon? Walk me through how we'd adapt the spec to use Mongo Atlas instead of Postgres + pgvector. I want honest assessment of what's harder, what's the same, and whether this is actually a good idea or if we should bite the bullet and add Postgres.

Read the repo at `/Users/Adam.Lenning/repos/personal/lexicon` and answer:

1. Should we use Mongo Atlas? (Yes/No, with honest reasoning — 2-3 paragraphs)
2. If yes, which parts of the spec need translation from the Postgres+pgvector defaults?
3. Which parts carry over unchanged?
4. What's specifically harder with Atlas vs Postgres for this use case?
5. What existing Atlas features should we lean on?
6. Docs you consulted
