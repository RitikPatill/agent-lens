from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anthropic import Anthropic as _AnthropicType
    from anthropic import AsyncAnthropic as _AsyncAnthropicType

from agentlens.client import TraceClient
from agentlens.models import SpanKind


class _TracedMessages:
    def __init__(self, inner: Any, trace_client: TraceClient) -> None:
        self._inner = inner
        self._tc = trace_client

    def create(self, *, model: str, messages: list[Any], **kwargs: Any) -> Any:
        span = self._tc.start_span(
            f"llm:{model}",
            kind=SpanKind.llm,
            attributes={"model": model, "input": messages},
        )
        try:
            response = self._inner.create(model=model, messages=messages, **kwargs)
            span.attributes.update(
                {
                    "output": response.content,
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                }
            )
            return response
        except Exception as exc:
            span.attributes["error"] = str(exc)
            raise
        finally:
            self._tc.end_span(span)


class _TracedAsyncMessages:
    def __init__(self, inner: Any, trace_client: TraceClient) -> None:
        self._inner = inner
        self._tc = trace_client

    async def create(self, *, model: str, messages: list[Any], **kwargs: Any) -> Any:
        span = self._tc.start_span(
            f"llm:{model}",
            kind=SpanKind.llm,
            attributes={"model": model, "input": messages},
        )
        try:
            response = await self._inner.create(model=model, messages=messages, **kwargs)
            span.attributes.update(
                {
                    "output": response.content,
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                }
            )
            return response
        except Exception as exc:
            span.attributes["error"] = str(exc)
            raise
        finally:
            self._tc.end_span(span)


class TracedAnthropic:
    """Drop-in for anthropic.Anthropic that auto-captures every messages.create call."""

    def __init__(self, api_key: str | None = None, *, trace_client: TraceClient) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError("Install anthropic: pip install agentlens[anthropic]") from e
        self._inner = Anthropic(api_key=api_key)
        self._tc = trace_client
        self.messages = _TracedMessages(self._inner.messages, trace_client)


class TracedAsyncAnthropic:
    """Drop-in for anthropic.AsyncAnthropic that auto-captures every messages.create call."""

    def __init__(self, api_key: str | None = None, *, trace_client: TraceClient) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("Install anthropic: pip install agentlens[anthropic]") from e
        self._inner = AsyncAnthropic(api_key=api_key)
        self._tc = trace_client
        self.messages = _TracedAsyncMessages(self._inner.messages, trace_client)
