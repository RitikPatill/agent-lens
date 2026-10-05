from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from agentlens.client import TraceClient
from agentlens.models import SpanKind, TraceEvent


class FakeClient(TraceClient):
    def __init__(self) -> None:
        super().__init__(collector_url="http://fake", flush_timeout=1.0)
        self.events: list[TraceEvent] = []

    def _emit(self, event: TraceEvent) -> None:
        self.events.append(event)

    def events_by_type(self, event_type: str) -> list[TraceEvent]:
        return [e for e in self.events if e.event_type == event_type]


def _make_mock_response(
    content: list[MagicMock] | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    response = MagicMock()
    response.content = content or [MagicMock(text="Hello")]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def test_traced_anthropic_emits_llm_span() -> None:
    from agentlens.anthropic_wrap import TracedAnthropic

    fc = FakeClient()
    mock_response = _make_mock_response(input_tokens=123, output_tokens=45)

    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = mock_response

        ta = TracedAnthropic(api_key="fake", trace_client=fc)
        # Replace the inner messages with the mock directly
        ta._inner = instance
        ta.messages._inner = instance.messages

        messages = [{"role": "user", "content": "hello"}]
        result = ta.messages.create(model="claude-3-haiku-20240307", messages=messages)

    assert result is mock_response

    starts = fc.events_by_type("span_start")
    ends = fc.events_by_type("span_end")
    assert len(starts) == 1
    assert len(ends) == 1

    span = ends[0].span
    assert span is not None
    assert span.kind == SpanKind.llm
    assert span.attributes["model"] == "claude-3-haiku-20240307"
    assert span.attributes["input"] == messages
    assert span.attributes["prompt_tokens"] == 123
    assert span.attributes["completion_tokens"] == 45
    assert span.attributes["output"] == mock_response.content


def test_traced_anthropic_span_name_contains_model() -> None:
    from agentlens.anthropic_wrap import TracedAnthropic

    fc = FakeClient()
    mock_response = _make_mock_response()

    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = mock_response

        ta = TracedAnthropic(api_key="fake", trace_client=fc)
        ta._inner = instance
        ta.messages._inner = instance.messages

        ta.messages.create(model="claude-sonnet-4-6", messages=[])

    starts = fc.events_by_type("span_start")
    assert starts[0].span is not None
    assert "claude-sonnet-4-6" in starts[0].span.name


def test_traced_anthropic_missing_dep_raises_import_error() -> None:
    """When anthropic is not installed, TracedAnthropic.__init__ raises ImportError."""
    # Temporarily hide anthropic from sys.modules
    original = sys.modules.get("anthropic")
    sys.modules["anthropic"] = None  # type: ignore[assignment]
    try:
        # Need to reload the module to re-trigger the import
        from agentlens.anthropic_wrap import TracedAnthropic
        from agentlens.client import TraceClient as TC

        fc2 = TC.__new__(TC)
        with pytest.raises(ImportError, match="pip install agentlens"):
            TracedAnthropic(trace_client=fc2)  # type: ignore[arg-type]
    finally:
        if original is None:
            del sys.modules["anthropic"]
        else:
            sys.modules["anthropic"] = original
