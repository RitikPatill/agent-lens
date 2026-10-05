from __future__ import annotations

import warnings
from datetime import timezone
from typing import Any

import httpx

from agentlens.context import (
    get_current_run_id,
    get_current_span_id,
    set_current_run_id,
    set_current_span_id,
)
from agentlens.models import Run, RunStatus, Span, SpanKind, TraceEvent


class TraceClient:
    def __init__(
        self,
        collector_url: str = "http://localhost:8080",
        *,
        flush_timeout: float = 5.0,
    ) -> None:
        self._collector_url = collector_url.rstrip("/")
        self._flush_timeout = flush_timeout

    # --- Run management ---

    def start_run(self, name: str, metadata: dict[str, Any] | None = None) -> Run:
        run = Run(name=name, metadata=metadata or {})
        token = set_current_run_id(run.run_id)
        # Store the token so end_run can reset — attach to run object for convenience
        run.__dict__["_ctx_token"] = token
        self._emit(TraceEvent(event_type="run_start", run=run))
        return run

    def end_run(self, run_id: str, *, status: RunStatus = RunStatus.completed) -> None:
        from datetime import datetime

        # We need the Run object; reconstruct a minimal one for the event
        run = Run(run_id=run_id, name="", status=status)
        run.ended_at = datetime.now(timezone.utc)
        run.status = status
        self._emit(TraceEvent(event_type="run_end", run=run))

    # --- Span management ---

    def start_span(
        self,
        name: str,
        kind: SpanKind,
        *,
        run_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        resolved_run_id = run_id or get_current_run_id() or "unset"
        resolved_parent = parent_span_id or get_current_span_id()
        span = Span(
            run_id=resolved_run_id,
            parent_span_id=resolved_parent,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        self._emit(TraceEvent(event_type="span_start", span=span))
        return span

    async def start_span_async(
        self,
        name: str,
        kind: SpanKind,
        *,
        run_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        resolved_run_id = run_id or get_current_run_id() or "unset"
        resolved_parent = parent_span_id or get_current_span_id()
        span = Span(
            run_id=resolved_run_id,
            parent_span_id=resolved_parent,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        await self._emit_async(TraceEvent(event_type="span_start", span=span))
        return span

    def end_span(self, span: Span, *, attributes: dict[str, Any] | None = None) -> None:
        from datetime import datetime

        span.ended_at = datetime.now(timezone.utc)
        if attributes:
            span.attributes.update(attributes)
        self._emit(TraceEvent(event_type="span_end", span=span))

    async def end_span_async(self, span: Span, *, attributes: dict[str, Any] | None = None) -> None:
        from datetime import datetime

        span.ended_at = datetime.now(timezone.utc)
        if attributes:
            span.attributes.update(attributes)
        await self._emit_async(TraceEvent(event_type="span_end", span=span))

    # --- Internal ---

    def _emit(self, event: TraceEvent) -> None:
        try:
            httpx.post(
                f"{self._collector_url}/v1/traces",
                content=event.model_dump_json(),
                headers={"Content-Type": "application/json"},
                timeout=self._flush_timeout,
            )
        except Exception as exc:
            warnings.warn(
                f"AgentLens: failed to emit {event.event_type} to collector: {exc}",
                stacklevel=2,
            )

    async def _emit_async(self, event: TraceEvent) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self._collector_url}/v1/traces",
                    content=event.model_dump_json(),
                    headers={"Content-Type": "application/json"},
                    timeout=self._flush_timeout,
                )
        except Exception as exc:
            warnings.warn(
                f"AgentLens: failed to emit {event.event_type} to collector: {exc}",
                stacklevel=2,
            )


# Module-level default client
_default_client: TraceClient | None = None


def configure(collector_url: str) -> None:
    global _default_client
    _default_client = TraceClient(collector_url=collector_url)


def get_default_client() -> TraceClient:
    global _default_client
    if _default_client is None:
        _default_client = TraceClient()
    return _default_client
