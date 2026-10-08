from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import Column, Index, MetaData, Table, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

metadata = MetaData()

runs_table = Table(
    "runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="running"),
    Column("started_at", Text, nullable=False),
    Column("ended_at", Text),
    Column("root_span_id", Text),
    Column("metadata", Text, nullable=False, server_default="{}"),
)

Index("idx_runs_status", runs_table.c.status)

spans_table = Table(
    "spans",
    metadata,
    Column("span_id", Text, primary_key=True),
    Column("run_id", Text, nullable=False),
    Column("parent_span_id", Text),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("started_at", Text, nullable=False),
    Column("ended_at", Text),
    Column("attributes", Text, nullable=False, server_default="{}"),
)

Index("idx_spans_run_id", spans_table.c.run_id)
Index("idx_spans_parent", spans_table.c.parent_span_id)

evals_table = Table(
    "evals",
    metadata,
    Column("eval_id", Text, primary_key=True),
    Column("run_id", Text, nullable=False),
    Column("rubric_name", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("reasoning", Text),
    Column("created_at", Text, nullable=False),
    Column("completed_at", Text),
)

Index("idx_evals_run_id", evals_table.c.run_id)

# Module-level engine — starts as None, set lazily in init_db()
engine: Any = None
AsyncSessionLocal: Any = None


async def init_db() -> None:
    global engine, AsyncSessionLocal
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentlens.db")
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def decode_run_row(row: Any) -> dict:
    return {
        "run_id": row.run_id,
        "name": row.name,
        "status": row.status,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "root_span_id": row.root_span_id,
        "metadata": json.loads(row.metadata) if row.metadata else {},
    }


def decode_span_row(row: Any) -> dict:
    return {
        "span_id": row.span_id,
        "run_id": row.run_id,
        "parent_span_id": row.parent_span_id,
        "name": row.name,
        "kind": row.kind,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "attributes": json.loads(row.attributes) if row.attributes else {},
    }


def decode_eval_row(row: Any) -> dict:
    return {
        "eval_id": row.eval_id,
        "run_id": row.run_id,
        "rubric_name": row.rubric_name,
        "status": row.status,
        "reasoning": row.reasoning,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }
