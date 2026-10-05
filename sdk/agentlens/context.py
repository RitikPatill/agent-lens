from __future__ import annotations

from contextvars import ContextVar, Token

_current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)
_current_span_id: ContextVar[str | None] = ContextVar("current_span_id", default=None)


def get_current_run_id() -> str | None:
    return _current_run_id.get()


def get_current_span_id() -> str | None:
    return _current_span_id.get()


def set_current_run_id(run_id: str) -> Token[str | None]:
    return _current_run_id.set(run_id)


def set_current_span_id(span_id: str) -> Token[str | None]:
    return _current_span_id.set(span_id)
