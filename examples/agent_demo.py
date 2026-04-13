"""End-to-end demo: an agent consulting lexicon before querying the warehouse.

v0 scaffold — runs against the stubbed MCP server and prints placeholder output.
Once v0.1 ships the underlying handlers, this will demonstrate the full flow:

    1. User: "What's our MRR for March?"
    2. Agent calls lexicon.define("MRR") → gets the org's exact definition
    3. Agent calls lexicon.get_canonical_query("mrr_by_month", {"start": "2026-03-01", ...})
    4. Agent executes the returned SQL against Snowflake (outside lexicon's scope)
    5. Agent returns the answer grounded in the canonical definition

For now this file is documentation, not a runnable demo.
"""

from __future__ import annotations


def main() -> None:
    print(
        "This is a scaffold. See DESIGN.md §9 for the v0.1 milestone when this demo becomes real."
    )


if __name__ == "__main__":
    main()
