from __future__ import annotations

import asyncio
import functools
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, TypeVar

from agentlens.context import set_current_span_id
from agentlens.models import SpanKind

F = TypeVar("F", bound=Callable[..., Any])


def _get_client(client: Any) -> Any:
    from agentlens.client import get_default_client

    return client if client is not None else get_default_client()


def traced(
    name: str | None = None,
    *,
    kind: SpanKind = SpanKind.agent,
    client: Any = None,
) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        span_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tc = _get_client(client)
                span = await tc.start_span_async(span_name, kind)
                token = set_current_span_id(span.span_id)
                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.attributes["error"] = str(exc)
                    raise
                finally:
                    await tc.end_span_async(span)
                    from agentlens.context import _current_span_id

                    _current_span_id.reset(token)

            return async_wrapper  # type: ignore[return-value]

        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tc = _get_client(client)
                span = tc.start_span(span_name, kind)
                token = set_current_span_id(span.span_id)
                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.attributes["error"] = str(exc)
                    raise
                finally:
                    tc.end_span(span)
                    from agentlens.context import _current_span_id

                    _current_span_id.reset(token)

            return sync_wrapper  # type: ignore[return-value]

    return decorator


@contextmanager
def span(
    name: str,
    *,
    kind: SpanKind = SpanKind.agent,
    client: Any = None,
    **attributes: Any,
) -> Generator[Any, None, None]:
    from agentlens.context import _current_span_id

    tc = _get_client(client)
    s = tc.start_span(name, kind, attributes=attributes if attributes else None)
    token = set_current_span_id(s.span_id)
    try:
        yield s
    except Exception as exc:
        s.attributes["error"] = str(exc)
        raise
    finally:
        tc.end_span(s)
        _current_span_id.reset(token)


@asynccontextmanager
async def async_span(
    name: str,
    *,
    kind: SpanKind = SpanKind.agent,
    client: Any = None,
    **attributes: Any,
) -> AsyncGenerator[Any, None]:
    from agentlens.context import _current_span_id

    tc = _get_client(client)
    s = await tc.start_span_async(name, kind, attributes=attributes if attributes else None)
    token = set_current_span_id(s.span_id)
    try:
        yield s
    except Exception as exc:
        s.attributes["error"] = str(exc)
        raise
    finally:
        await tc.end_span_async(s)
        _current_span_id.reset(token)
