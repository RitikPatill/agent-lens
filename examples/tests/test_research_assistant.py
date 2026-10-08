"""Tests for examples/research_assistant.py — no real API calls."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Allow importing from the examples/ directory regardless of cwd
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.research_assistant import mock_search, main  # noqa: E402


# ---------------------------------------------------------------------------
# mock_search unit tests
# ---------------------------------------------------------------------------


def test_mock_search_hit():
    result = mock_search("starship landing procedure")
    assert result and result != "No results found."
    assert len(result) > 20


def test_mock_search_miss():
    result = mock_search("xyzzy irrelevant nonsense query")
    assert result == "No results found."


# ---------------------------------------------------------------------------
# Full pipeline test with mocked LLM
# ---------------------------------------------------------------------------


def _make_llm_mock(call_count_ref: list[int]) -> MagicMock:
    """Return a TracedAsyncAnthropic-shaped mock whose messages.create is async."""

    def _create_side_effect(*args, **kwargs):
        call_count_ref[0] += 1
        idx = call_count_ref[0]

        if idx == 1:
            # Planner call — return JSON array of 2 queries
            mock_resp = MagicMock()
            mock_resp.content = [MagicMock(text='["starship landing", "spacex starship"]')]
            mock_resp.usage = MagicMock(input_tokens=10, output_tokens=20)
            return mock_resp
        else:
            # Researcher or writer calls — return plain text
            mock_resp = MagicMock()
            mock_resp.content = [
                MagicMock(
                    text=(
                        "SpaceX caught the Super Heavy booster with Mechazilla. "
                        "[Source: starship landing]"
                    )
                )
            ]
            mock_resp.usage = MagicMock(input_tokens=10, output_tokens=20)
            return mock_resp

    messages_mock = MagicMock()
    messages_mock.create = AsyncMock(side_effect=_create_side_effect)

    llm_mock = MagicMock()
    llm_mock.messages = messages_mock
    return llm_mock


def test_pipeline_runs(monkeypatch):
    """Full pipeline with mocked Anthropic — expects ≥4 LLM calls, no exceptions."""
    call_count: list[int] = [0]

    llm_mock = _make_llm_mock(call_count)

    # Patch TraceClient methods to be no-ops so no HTTP calls are made
    monkeypatch.setattr(
        "agentlens.client.TraceClient._emit",
        lambda self, event: None,
    )
    monkeypatch.setattr(
        "agentlens.client.TraceClient._emit_async",
        AsyncMock(),
    )

    # Patch TracedAsyncAnthropic constructor to return our mock
    with patch(
        "examples.research_assistant.TracedAsyncAnthropic",
        return_value=llm_mock,
    ):
        asyncio.run(main("test question about starship"))

    # 1 planner + 2 researchers + 1 writer = 4 minimum
    assert call_count[0] >= 4, f"Expected ≥4 LLM calls, got {call_count[0]}"
