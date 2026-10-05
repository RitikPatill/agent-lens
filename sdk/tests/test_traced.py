from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agentlens.client import TraceClient
from agentlens.context import get_current_span_id, _current_span_id
from agentlens.decorators import async_span, span, traced
from agentlens.models import SpanKind, TraceEvent


class FakeClient(TraceClient):
    """TraceClient that records events instead of POSTing them."""

    def __init__(self) -> None:
        super().__init__(collector_url="http://fake", flush_timeout=1.0)
        self.events: list[TraceEvent] = []

    def _emit(self, event: TraceEvent) -> None:  # type: ignore[override]
        self.events.append(event)

    async def _emit_async(self, event: TraceEvent) -> None:  # type: ignore[override]
        self.events.append(event)

    def span_events(self) -> list[TraceEvent]:
        return [e for e in self.events if e.span is not None]

    def events_by_type(self, event_type: str) -> list[TraceEvent]:
        return [e for e in self.events if e.event_type == event_type]


# --- @traced sync ---

def test_traced_sync_emits_span_start_and_end() -> None:
    fc = FakeClient()

    @traced(client=fc)
    def my_fn() -> str:
        return "ok"

    my_fn()

    starts = fc.events_by_type("span_start")
    ends = fc.events_by_type("span_end")
    assert len(starts) == 1
    assert len(ends) == 1
    assert starts[0].span is not None
    assert starts[0].span.name == "my_fn"


def test_traced_sync_custom_name() -> None:
    fc = FakeClient()

    @traced(name="custom", client=fc)
    def fn() -> None:
        pass

    fn()
    assert fc.events_by_type("span_start")[0].span.name == "custom"  # type: ignore[union-attr]


def test_traced_sync_exception_sets_error_and_still_ends() -> None:
    fc = FakeClient()

    @traced(client=fc)
    def bad_fn() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        bad_fn()

    ends = fc.events_by_type("span_end")
    assert len(ends) == 1
    assert ends[0].span is not None
    assert ends[0].span.attributes.get("error") == "boom"


# --- @traced async ---

async def _run_async_traced(fc: FakeClient) -> None:
    @traced(client=fc)
    async def async_fn() -> str:
        return "async-ok"

    await async_fn()


def test_traced_async_emits_span_start_and_end() -> None:
    fc = FakeClient()
    asyncio.run(_run_async_traced(fc))

    starts = fc.events_by_type("span_start")
    ends = fc.events_by_type("span_end")
    assert len(starts) == 1
    assert len(ends) == 1
    assert starts[0].span is not None
    assert starts[0].span.name == "async_fn"


def test_traced_async_exception_sets_error() -> None:
    fc = FakeClient()

    @traced(client=fc)
    async def bad_async() -> None:
        raise RuntimeError("async-boom")

    with pytest.raises(RuntimeError):
        asyncio.run(bad_async())

    ends = fc.events_by_type("span_end")
    assert ends[0].span is not None
    assert ends[0].span.attributes.get("error") == "async-boom"


# --- Nested spans and parent_span_id ---

def test_nested_traced_sets_parent_span_id() -> None:
    fc = FakeClient()

    @traced(client=fc)
    def outer() -> None:
        inner()

    @traced(client=fc)
    def inner() -> None:
        pass

    outer()

    starts = fc.events_by_type("span_start")
    assert len(starts) == 2
    outer_span = starts[0].span
    inner_span = starts[1].span
    assert outer_span is not None
    assert inner_span is not None
    assert inner_span.parent_span_id == outer_span.span_id


def test_context_var_restored_after_traced() -> None:
    fc = FakeClient()

    @traced(client=fc)
    def fn() -> None:
        pass

    # Before call: no span in context
    assert get_current_span_id() is None
    fn()
    # After call: context restored
    assert get_current_span_id() is None


# --- span() context manager ---

def test_span_context_manager_emits_events() -> None:
    fc = FakeClient()

    with span("my-span", kind=SpanKind.tool, client=fc) as s:
        assert s.name == "my-span"
        assert s.kind == SpanKind.tool

    starts = fc.events_by_type("span_start")
    ends = fc.events_by_type("span_end")
    assert len(starts) == 1
    assert len(ends) == 1


def test_span_context_manager_restores_context() -> None:
    fc = FakeClient()

    assert get_current_span_id() is None
    with span("s1", client=fc):
        pass
    assert get_current_span_id() is None


def test_span_nested_context_restoration() -> None:
    fc = FakeClient()

    with span("outer", client=fc) as outer_s:
        outer_id = get_current_span_id()
        with span("inner", client=fc):
            inner_id = get_current_span_id()
            assert inner_id != outer_id
        # After inner exits, context should be back to outer
        assert get_current_span_id() == outer_s.span_id


# --- async_span() ---

async def _run_async_span(fc: FakeClient) -> None:
    async with async_span("async-span", kind=SpanKind.memory, client=fc) as s:
        assert s.name == "async-span"


def test_async_span_works() -> None:
    fc = FakeClient()
    asyncio.run(_run_async_span(fc))

    starts = fc.events_by_type("span_start")
    ends = fc.events_by_type("span_end")
    assert len(starts) == 1
    assert len(ends) == 1
    assert starts[0].span is not None
    assert starts[0].span.kind == SpanKind.memory
