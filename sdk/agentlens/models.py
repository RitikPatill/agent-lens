from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SpanKind(StrEnum):
    llm = "llm"
    tool = "tool"
    agent = "agent"
    memory = "memory"
    retry = "retry"


class RunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: RunStatus = RunStatus.running
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    root_span_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    parent_span_id: str | None = None
    name: str
    kind: SpanKind
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(BaseModel):
    event_type: Literal["run_start", "run_end", "span_start", "span_end"]
    run: Run | None = None
    span: Span | None = None
