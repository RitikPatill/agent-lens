from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from agentlens.models import TraceEvent

from .db import decode_run_row, decode_span_row, get_db, init_db
from .sse import broadcaster


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="AgentLens Collector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/traces")
async def ingest_trace(event: TraceEvent):
    async for db in get_db():
        if event.event_type == "run_start" and event.run is not None:
            run = event.run
            await db.execute(
                text(
                    "INSERT OR IGNORE INTO runs "
                    "(run_id, name, status, started_at, ended_at, root_span_id, metadata) "
                    "VALUES (:run_id, :name, :status, :started_at, :ended_at, :root_span_id, :metadata)"
                ),
                {
                    "run_id": run.run_id,
                    "name": run.name,
                    "status": run.status.value,
                    "started_at": run.started_at.isoformat(),
                    "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                    "root_span_id": run.root_span_id,
                    "metadata": json.dumps(run.metadata),
                },
            )
            await db.commit()

        elif event.event_type == "run_end" and event.run is not None:
            run = event.run
            await db.execute(
                text(
                    "UPDATE runs SET status = :status, ended_at = :ended_at "
                    "WHERE run_id = :run_id"
                ),
                {
                    "status": run.status.value,
                    "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                    "run_id": run.run_id,
                },
            )
            await db.commit()

        elif event.event_type == "span_start" and event.span is not None:
            span = event.span
            await db.execute(
                text(
                    "INSERT OR IGNORE INTO spans "
                    "(span_id, run_id, parent_span_id, name, kind, started_at, ended_at, attributes) "
                    "VALUES (:span_id, :run_id, :parent_span_id, :name, :kind, :started_at, :ended_at, :attributes)"
                ),
                {
                    "span_id": span.span_id,
                    "run_id": span.run_id,
                    "parent_span_id": span.parent_span_id,
                    "name": span.name,
                    "kind": span.kind.value,
                    "started_at": span.started_at.isoformat(),
                    "ended_at": span.ended_at.isoformat() if span.ended_at else None,
                    "attributes": json.dumps(span.attributes),
                },
            )
            await db.commit()

        elif event.event_type == "span_end" and event.span is not None:
            span = event.span
            # Merge attributes: read existing, update with incoming
            result = await db.execute(
                text("SELECT attributes FROM spans WHERE span_id = :span_id"),
                {"span_id": span.span_id},
            )
            row = result.fetchone()
            if row is not None:
                existing_attrs = json.loads(row[0]) if row[0] else {}
                existing_attrs.update(span.attributes)
                merged = json.dumps(existing_attrs)
            else:
                merged = json.dumps(span.attributes)

            await db.execute(
                text(
                    "UPDATE spans SET ended_at = :ended_at, attributes = :attributes "
                    "WHERE span_id = :span_id"
                ),
                {
                    "ended_at": span.ended_at.isoformat() if span.ended_at else None,
                    "attributes": merged,
                    "span_id": span.span_id,
                },
            )
            await db.commit()

    await broadcaster.publish(event.model_dump_json())
    return {"ok": True}


@app.get("/v1/runs")
async def list_runs():
    async for db in get_db():
        result = await db.execute(
            text("SELECT * FROM runs ORDER BY started_at DESC")
        )
        rows = result.fetchall()
        return [decode_run_row(row) for row in rows]


@app.get("/v1/runs/{run_id}/spans")
async def list_spans(run_id: str):
    async for db in get_db():
        result = await db.execute(
            text("SELECT * FROM spans WHERE run_id = :run_id ORDER BY started_at ASC"),
            {"run_id": run_id},
        )
        rows = result.fetchall()
        return [decode_span_row(row) for row in rows]


@app.get("/v1/stream")
async def stream(request: Request):
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        q = broadcaster.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {"data": data}
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        finally:
            broadcaster.unsubscribe(q)

    return EventSourceResponse(event_generator())
