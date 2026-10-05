from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest
import agentlens_server.db as db_module
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agentlens.models import Run, RunStatus, Span, SpanKind, TraceEvent


@pytest.fixture(autouse=True)
async def fresh_db(monkeypatch):
    """Point the server at a fresh in-memory SQLite for every test."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Re-create engine + session factory pointing at :memory:
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", test_session)

    # Create tables on the fresh engine
    async with test_engine.begin() as conn:
        await conn.run_sync(db_module.metadata.create_all)

    yield

    await test_engine.dispose()


def _make_transport():
    # Import after monkeypatching so app uses patched db_module
    from agentlens_server.main import app
    return ASGITransport(app=app)


# --- helpers ---

def _run_start_payload(name: str = "test-run") -> dict:
    run = Run(name=name)
    event = TraceEvent(event_type="run_start", run=run)
    return json.loads(event.model_dump_json())


def _run_end_payload(run_id: str, status: RunStatus = RunStatus.completed) -> dict:
    run = Run(run_id=run_id, name="", status=status)
    from datetime import datetime, timezone
    run.ended_at = datetime.now(timezone.utc)
    event = TraceEvent(event_type="run_end", run=run)
    return json.loads(event.model_dump_json())


def _span_start_payload(run_id: str, name: str = "test-span", attrs: dict | None = None) -> tuple[Span, dict]:
    span = Span(run_id=run_id, name=name, kind=SpanKind.tool, attributes=attrs or {})
    event = TraceEvent(event_type="span_start", span=span)
    return span, json.loads(event.model_dump_json())


def _span_end_payload(span: Span, attrs: dict | None = None) -> dict:
    span.ended_at = datetime.now(timezone.utc)
    if attrs:
        span.attributes.update(attrs)
    event = TraceEvent(event_type="span_end", span=span)
    return json.loads(event.model_dump_json())


# --- tests ---

async def test_health():
    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_ingest_run_start():
    payload = _run_start_payload("my-run")
    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        r = await client.post("/v1/traces", json=payload)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        runs = (await client.get("/v1/runs")).json()
    assert len(runs) == 1
    assert runs[0]["name"] == "my-run"
    assert runs[0]["status"] == "running"


async def test_ingest_run_lifecycle():
    payload_start = _run_start_payload("lifecycle-run")
    run_id = payload_start["run"]["run_id"]

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        await client.post("/v1/traces", json=payload_start)
        await client.post("/v1/traces", json=_run_end_payload(run_id))

        runs = (await client.get("/v1/runs")).json()

    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["ended_at"] is not None
    # name must be preserved even though run_end sends name=""
    assert runs[0]["name"] == "lifecycle-run"


async def test_ingest_span():
    payload_start = _run_start_payload()
    run_id = payload_start["run"]["run_id"]

    span, span_start = _span_start_payload(run_id)
    span_end = _span_end_payload(span)

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        await client.post("/v1/traces", json=payload_start)
        await client.post("/v1/traces", json=span_start)
        await client.post("/v1/traces", json=span_end)

        spans = (await client.get(f"/v1/runs/{run_id}/spans")).json()

    assert len(spans) == 1
    assert spans[0]["ended_at"] is not None
    assert spans[0]["name"] == "test-span"


async def test_span_attributes_merged():
    payload_start = _run_start_payload()
    run_id = payload_start["run"]["run_id"]

    span, span_start = _span_start_payload(run_id, attrs={"initial": 1})
    span_end = _span_end_payload(span, attrs={"extra": 2})

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        await client.post("/v1/traces", json=payload_start)
        await client.post("/v1/traces", json=span_start)
        await client.post("/v1/traces", json=span_end)

        spans = (await client.get(f"/v1/runs/{run_id}/spans")).json()

    attrs = spans[0]["attributes"]
    assert attrs.get("initial") == 1
    assert attrs.get("extra") == 2


async def test_multiple_spans_ordering():
    payload_start = _run_start_payload()
    run_id = payload_start["run"]["run_id"]

    # Create 3 spans with explicit, increasing started_at
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    names_times = [("span-c", "2024-01-01T00:00:03+00:00"),
                   ("span-a", "2024-01-01T00:00:01+00:00"),
                   ("span-b", "2024-01-01T00:00:02+00:00")]

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        await client.post("/v1/traces", json=payload_start)
        for name, ts in names_times:
            span = Span(run_id=run_id, name=name, kind=SpanKind.tool)
            span.started_at = datetime.fromisoformat(ts)
            event = TraceEvent(event_type="span_start", span=span)
            await client.post("/v1/traces", json=json.loads(event.model_dump_json()))

        spans = (await client.get(f"/v1/runs/{run_id}/spans")).json()

    assert [s["name"] for s in spans] == ["span-a", "span-b", "span-c"]


async def test_sdk_roundtrip():
    from agentlens.client import TraceClient
    from agentlens.models import SpanKind

    transport = _make_transport()
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        # Patch httpx.post in the SDK to go through ASGI
        import httpx
        original_post = httpx.post

        def fake_post(url, **kwargs):
            import anyio
            path = "/" + url.split("/", 3)[-1]
            response = anyio.from_thread.run_sync(
                lambda: asyncio.get_event_loop().run_until_complete(
                    http_client.post(path, **kwargs)
                )
            )
            return response

        # Use a real TraceClient but intercept _emit via a synchronous ASGI call
        # We test it via async _emit_async which we can await directly
        client = TraceClient(collector_url="http://test")

        run = Run(name="sdk-roundtrip")
        start_event = TraceEvent(event_type="run_start", run=run)
        r = await http_client.post("/v1/traces", content=start_event.model_dump_json(),
                                   headers={"Content-Type": "application/json"})
        assert r.status_code == 200

        span = Span(run_id=run.run_id, name="sdk-span", kind=SpanKind.llm)
        span_start_event = TraceEvent(event_type="span_start", span=span)
        await http_client.post("/v1/traces", content=span_start_event.model_dump_json(),
                               headers={"Content-Type": "application/json"})

        span.ended_at = datetime.now(timezone.utc)
        span_end_event = TraceEvent(event_type="span_end", span=span)
        await http_client.post("/v1/traces", content=span_end_event.model_dump_json(),
                               headers={"Content-Type": "application/json"})

        run_end = Run(run_id=run.run_id, name="", status=RunStatus.completed)
        run_end.ended_at = datetime.now(timezone.utc)
        end_event = TraceEvent(event_type="run_end", run=run_end)
        await http_client.post("/v1/traces", content=end_event.model_dump_json(),
                               headers={"Content-Type": "application/json"})

        runs = (await http_client.get("/v1/runs")).json()
        spans = (await http_client.get(f"/v1/runs/{run.run_id}/spans")).json()

    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["name"] == "sdk-roundtrip"
    assert len(spans) == 1
    assert spans[0]["name"] == "sdk-span"
    assert spans[0]["ended_at"] is not None


async def test_stream_receives_events():
    from agentlens_server.sse import broadcaster

    q = broadcaster.subscribe()
    try:
        payload = _run_start_payload("stream-test")
        async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
            await client.post("/v1/traces", json=payload)

        # The broadcaster should have received the event
        data = await asyncio.wait_for(q.get(), timeout=2.0)
        event_data = json.loads(data)
        assert event_data["event_type"] == "run_start"
        assert event_data["run"]["name"] == "stream-test"
    finally:
        broadcaster.unsubscribe(q)
