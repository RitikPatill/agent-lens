from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
import agentlens_server.db as db_module
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agentlens.models import Run, RunStatus, TraceEvent
from agentlens_server.eval_runner import load_rubrics, serialize_trace


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def fresh_db(monkeypatch):
    """Point the server at a fresh in-memory SQLite for every test."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", test_session)

    async with test_engine.begin() as conn:
        await conn.run_sync(db_module.metadata.create_all)

    yield

    await test_engine.dispose()


def _make_transport():
    from agentlens_server.main import app
    return ASGITransport(app=app)


# ---------------------------------------------------------------------------
# Test 1: load_rubrics returns only enabled rubrics
# ---------------------------------------------------------------------------


def test_load_rubrics_enabled_only(tmp_path):
    enabled = tmp_path / "enabled.yaml"
    enabled.write_text(
        "name: enabled_rubric\ndescription: test\nenabled: true\n"
        "judge_prompt: 'judge {trace_json}'\npass_criteria: always\n"
    )
    disabled = tmp_path / "disabled.yaml"
    disabled.write_text(
        "name: disabled_rubric\ndescription: test\nenabled: false\n"
        "judge_prompt: 'judge {trace_json}'\npass_criteria: never\n"
    )

    rubrics = load_rubrics(str(tmp_path))
    assert len(rubrics) == 1
    assert rubrics[0]["name"] == "enabled_rubric"


# ---------------------------------------------------------------------------
# Test 2: load_rubrics on empty dir returns []
# ---------------------------------------------------------------------------


def test_load_rubrics_empty_dir(tmp_path):
    rubrics = load_rubrics(str(tmp_path))
    assert rubrics == []


# ---------------------------------------------------------------------------
# Test 3: serialize_trace returns JSON containing span names
# ---------------------------------------------------------------------------


async def test_serialize_trace():
    run_id = str(uuid.uuid4())
    span_id_1 = str(uuid.uuid4())
    span_id_2 = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with db_module.AsyncSessionLocal() as db:
        await db.execute(
            text(
                "INSERT INTO runs (run_id, name, status, started_at, metadata) "
                "VALUES (:run_id, :name, 'completed', :started_at, '{}')"
            ),
            {"run_id": run_id, "name": "test-run", "started_at": now},
        )
        await db.execute(
            text(
                "INSERT INTO spans (span_id, run_id, name, kind, started_at, attributes) "
                "VALUES (:span_id, :run_id, :name, 'tool', :started_at, '{}')"
            ),
            {"span_id": span_id_1, "run_id": run_id, "name": "search-web", "started_at": now},
        )
        await db.execute(
            text(
                "INSERT INTO spans (span_id, run_id, name, kind, started_at, attributes) "
                "VALUES (:span_id, :run_id, :name, 'llm', :started_at, '{}')"
            ),
            {"span_id": span_id_2, "run_id": run_id, "name": "generate-answer", "started_at": now},
        )
        await db.commit()

        trace_json = await serialize_trace(run_id, db)

    spans = json.loads(trace_json)
    names = [s["name"] for s in spans]
    assert "search-web" in names
    assert "generate-answer" in names


# ---------------------------------------------------------------------------
# Test 4: GET /v1/runs/{id}/evals returns [] when no evals exist
# ---------------------------------------------------------------------------


async def test_evals_endpoint_empty():
    run_id = str(uuid.uuid4())
    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        resp = await client.get(f"/v1/runs/{run_id}/evals")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Test 5: run_end event triggers run_evals_for_run (mock)
# ---------------------------------------------------------------------------


async def test_run_end_triggers_evals(monkeypatch):
    called_with: list[str] = []

    async def mock_run_evals(run_id: str, rubrics_dir=None) -> None:
        called_with.append(run_id)

    import agentlens_server.main as main_module
    monkeypatch.setattr(main_module, "run_evals_for_run", mock_run_evals)

    run = Run(name="trigger-test")
    start_event = TraceEvent(event_type="run_start", run=run)
    end_event = TraceEvent(event_type="run_end", run=Run(run_id=run.run_id, name="trigger-test", status=RunStatus.completed))

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        await client.post("/v1/traces", content=start_event.model_dump_json(), headers={"content-type": "application/json"})
        await client.post("/v1/traces", content=end_event.model_dump_json(), headers={"content-type": "application/json"})

    # Give the background task a chance to run
    import asyncio
    await asyncio.sleep(0.05)

    assert run.run_id in called_with


# ---------------------------------------------------------------------------
# Test 6: GET /v1/runs/{id}/evals returns inserted eval rows
# ---------------------------------------------------------------------------


async def test_evals_endpoint_returns_results():
    run_id = str(uuid.uuid4())
    eval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with db_module.AsyncSessionLocal() as db:
        await db.execute(
            text(
                "INSERT INTO evals (eval_id, run_id, rubric_name, status, reasoning, created_at, completed_at) "
                "VALUES (:eval_id, :run_id, :rubric_name, :status, :reasoning, :created_at, :completed_at)"
            ),
            {
                "eval_id": eval_id,
                "run_id": run_id,
                "rubric_name": "cites_sources",
                "status": "pass",
                "reasoning": "Agent cited two sources.",
                "created_at": now,
                "completed_at": now,
            },
        )
        await db.commit()

    async with AsyncClient(transport=_make_transport(), base_url="http://test") as client:
        resp = await client.get(f"/v1/runs/{run_id}/evals")

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    result = results[0]
    assert result["eval_id"] == eval_id
    assert result["run_id"] == run_id
    assert result["rubric_name"] == "cites_sources"
    assert result["status"] == "pass"
    assert result["reasoning"] == "Agent cited two sources."
    assert result["created_at"] == now
    assert result["completed_at"] == now
