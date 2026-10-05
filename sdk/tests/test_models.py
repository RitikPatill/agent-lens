from __future__ import annotations

from datetime import timezone

import pytest

from agentlens.models import Run, RunStatus, Span, SpanKind, TraceEvent


def test_run_defaults() -> None:
    run = Run(name="test-run")
    assert run.run_id  # non-empty string
    assert run.status == RunStatus.running
    assert run.started_at.tzinfo == timezone.utc
    assert run.ended_at is None
    assert run.root_span_id is None
    assert run.metadata == {}


def test_run_unique_ids() -> None:
    r1 = Run(name="a")
    r2 = Run(name="b")
    assert r1.run_id != r2.run_id


def test_span_defaults() -> None:
    span = Span(run_id="abc", name="my-span", kind=SpanKind.llm)
    assert span.span_id
    assert span.parent_span_id is None
    assert span.ended_at is None
    assert span.attributes == {}
    assert span.started_at.tzinfo == timezone.utc


def test_span_kind_serializes_to_string() -> None:
    assert SpanKind.llm == "llm"
    assert SpanKind.tool == "tool"
    assert SpanKind.agent == "agent"
    assert SpanKind.memory == "memory"
    assert SpanKind.retry == "retry"
    # Should serialize without .value
    span = Span(run_id="x", name="s", kind=SpanKind.llm)
    data = span.model_dump()
    assert data["kind"] == "llm"


def test_run_status_serializes_to_string() -> None:
    assert RunStatus.running == "running"
    assert RunStatus.completed == "completed"
    assert RunStatus.failed == "failed"
    run = Run(name="r", status=RunStatus.failed)
    data = run.model_dump()
    assert data["status"] == "failed"


def test_run_status_default_is_running() -> None:
    run = Run(name="r")
    assert run.status == RunStatus.running


def test_trace_event_round_trip_run_start() -> None:
    run = Run(name="trip")
    event = TraceEvent(event_type="run_start", run=run)
    dumped = event.model_dump()
    reloaded = TraceEvent.model_validate(dumped)
    assert reloaded.event_type == "run_start"
    assert reloaded.run is not None
    assert reloaded.run.run_id == run.run_id
    assert reloaded.span is None


def test_trace_event_round_trip_span_end() -> None:
    span = Span(run_id="r", name="s", kind=SpanKind.tool)
    event = TraceEvent(event_type="span_end", span=span)
    dumped = event.model_dump()
    reloaded = TraceEvent.model_validate(dumped)
    assert reloaded.event_type == "span_end"
    assert reloaded.span is not None
    assert reloaded.span.span_id == span.span_id
    assert reloaded.run is None


def test_trace_event_json_round_trip() -> None:
    run = Run(name="json-trip")
    event = TraceEvent(event_type="run_end", run=run)
    json_str = event.model_dump_json()
    reloaded = TraceEvent.model_validate_json(json_str)
    assert reloaded.run is not None
    assert reloaded.run.name == "json-trip"
