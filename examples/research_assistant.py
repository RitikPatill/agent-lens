"""
research_assistant.py — AgentLens M7 example

Planner → 2× Researcher (parallel) → Writer pipeline.
Uses TracedAsyncAnthropic so every LLM call is captured as a span.

Usage:
    python examples/research_assistant.py "How did SpaceX land Starship?"
"""

from __future__ import annotations

import asyncio
import json
import sys

from agentlens import (
    RunStatus,
    SpanKind,
    TracedAsyncAnthropic,
    async_span,
    configure,
    traced,
)
from agentlens.client import get_default_client

# ---------------------------------------------------------------------------
# Canned search fixtures — no paid search API needed
# ---------------------------------------------------------------------------

SEARCH_DB: dict[str, str] = {
    "starship landing": (
        "SpaceX successfully caught the Super Heavy booster with the Mechazilla "
        "mechanical arm system ('chopstick' arms) on the launch tower during the "
        "fifth integrated flight test on October 13, 2024. The booster returned to "
        "the launch site and was grabbed mid-air by the tower arms, marking the "
        "first time a rocket booster had been caught rather than landing on legs."
    ),
    "starship booster catch": (
        "The Mechazilla tower catch of the Super Heavy booster used two giant "
        "mechanical arms nicknamed 'chopsticks' mounted on the Starbase launch "
        "tower in Boca Chica, Texas. The arms closed around the booster as it "
        "descended, eliminating the need for landing legs and enabling rapid "
        "reuse. The first successful catch occurred on IFT-5 in October 2024."
    ),
    "spacex starship": (
        "Starship is SpaceX's fully reusable two-stage launch vehicle consisting "
        "of the Super Heavy booster and the Starship upper stage. Standing about "
        "121 metres tall, it is the largest and most powerful rocket ever built, "
        "designed for missions to the Moon, Mars, and point-to-point Earth travel."
    ),
    "starship super heavy": (
        "Super Heavy is the first-stage booster of the Starship system. It is "
        "powered by up to 33 Raptor engines burning liquid methane and liquid "
        "oxygen (methalox). The booster produces about 74 MN (16.7 million lbf) "
        "of thrust at liftoff and is designed to be caught and reused within hours."
    ),
    "spacex reusable rocket": (
        "SpaceX pioneered booster reusability with Falcon 9, which lands its "
        "first stage on drone ships or landing pads after each flight. Starship "
        "extends this to full vehicle reusability: both the Super Heavy booster "
        "and the Starship upper stage are designed to return and be reflown, "
        "targeting turnaround times measured in hours rather than months."
    ),
    "starship orbital test": (
        "Starship completed its first fully successful integrated flight test "
        "(IFT-5) on October 13, 2024, with the booster caught by Mechazilla and "
        "the Ship completing a controlled ocean splashdown. Earlier tests IFT-1 "
        "through IFT-4 progressively demonstrated stage separation, controlled "
        "flight, and reentry survivability."
    ),
    "spacex starship fuel": (
        "Starship uses liquid methane (CH₄) and liquid oxygen (LOX) as propellants, "
        "a combination known as methalox. SpaceX chose methane because it can be "
        "synthesized on Mars from atmospheric CO₂ and water ice, enabling "
        "in-situ propellant production for return trips. Each Raptor engine "
        "consumes methalox at extreme pressures exceeding 300 bar."
    ),
    "mechazilla tower": (
        "Mechazilla (officially the 'Mechazilla' catch system) is the launch-and-"
        "catch tower at SpaceX's Starbase facility. Two large mechanical arms "
        "('chopsticks') mounted on the tower are used to catch the returning "
        "Super Heavy booster and to lift the Starship onto the booster for "
        "stacking. The system is central to SpaceX's rapid reuse ambitions."
    ),
    "booster catch attempt": (
        "The first successful booster catch happened during IFT-5 on October 13, "
        "2024. The Super Heavy booster performed a boostback burn, re-entry burn, "
        "and landing burn before being caught by the Mechazilla chopstick arms "
        "at Starbase. SpaceX CEO Elon Musk called it a historic moment in "
        "reusable rocketry."
    ),
    "starship heat shield": (
        "Starship's heat shield uses ~18,000 black hexagonal ceramic tiles bonded "
        "to the stainless-steel hull to protect against reentry temperatures "
        "exceeding 1,400 °C. SpaceX iteratively improved tile attachment and "
        "coverage through early flight tests; IFT-5 showed significantly better "
        "tile retention than previous flights, with the Ship completing a "
        "controlled splashdown in the Indian Ocean."
    ),
}


def mock_search(query: str) -> str:
    """Return a canned result for the closest matching key, or 'No results found.'"""
    q = query.lower()
    for key, value in SEARCH_DB.items():
        if key in q:
            return value
    return "No results found."


# ---------------------------------------------------------------------------
# Agent functions
# ---------------------------------------------------------------------------


@traced(kind=SpanKind.agent)
async def planner(question: str, llm: TracedAsyncAnthropic) -> list[str]:
    """Generate 2 distinct search queries for the given question."""
    resp = await llm.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system="Return ONLY a JSON array of exactly 2 search query strings, no other text.",
        messages=[
            {
                "role": "user",
                "content": f"Generate 2 distinct web search queries to answer: {question}",
            }
        ],
    )
    queries = json.loads(resp.content[0].text)
    # Attach metadata so rubrics can inspect the original question
    tc = get_default_client()
    tc  # noqa — attributes are set on the span by the decorator wrapper
    return queries


@traced(kind=SpanKind.agent)
async def researcher(query: str, llm: TracedAsyncAnthropic) -> str:
    """Search and summarise results for a single query."""
    async with async_span("web_search", kind=SpanKind.tool, query=query) as s:
        result = mock_search(query)
        s.attributes["result"] = result[:500]

    resp = await llm.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system="You are a research assistant. Summarise the provided search result concisely.",
        messages=[
            {
                "role": "user",
                "content": f"Query: {query}\n\nSearch result:\n{result}",
            }
        ],
    )
    return resp.content[0].text


@traced(kind=SpanKind.agent)
async def writer(
    question: str, research: list[str], queries: list[str], llm: TracedAsyncAnthropic
) -> str:
    """Compose the final answer from the research summaries."""
    research_block = "\n\n".join(
        f"[Source: {q}]\n{r}" for q, r in zip(queries, research)
    )
    resp = await llm.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "You are a helpful research writer. "
            "Always cite your sources inline using the format `[Source: <search query>]` "
            "when using information from research. "
            "Write a clear, well-structured answer to the user's question."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Research:\n{research_block}\n\n"
                    "Write a comprehensive answer to the question, citing sources."
                ),
            }
        ],
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def main(question: str) -> None:
    import os
    endpoint = os.environ.get("AGENTLENS_ENDPOINT", "http://localhost:8000")
    configure(endpoint)
    tc = get_default_client()
    llm = TracedAsyncAnthropic()

    run = tc.start_run("research_assistant", metadata={"question": question})
    try:
        # Step 1: Planner generates 2 search queries
        queries = await planner(question, llm)

        # Step 2: Two researchers run in parallel
        summaries = await asyncio.gather(
            researcher(queries[0], llm),
            researcher(queries[1], llm),
        )

        # Step 3: Writer composes the final answer
        answer = await writer(question, list(summaries), queries, llm)

        print("\n" + "=" * 60)
        print(f"Question: {question}")
        print("=" * 60)
        print(answer)
        print("=" * 60 + "\n")

        tc.end_run(run.run_id, status=RunStatus.completed)
    except Exception:
        tc.end_run(run.run_id, status=RunStatus.failed)
        raise


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "How did SpaceX land Starship?"))
