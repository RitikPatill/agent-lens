from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from glob import glob
from typing import Any

import anthropic
import yaml
from sqlalchemy import text

import agentlens_server.db as db_module
from .db import decode_eval_row


def load_rubrics(rubrics_dir: str) -> list[dict]:
    """Load all enabled rubrics from YAML files in rubrics_dir."""
    pattern = os.path.join(rubrics_dir, "*.yaml")
    rubrics = []
    for path in sorted(glob(pattern)):
        with open(path) as f:
            rubric = yaml.safe_load(f)
        if rubric.get("enabled", False):
            rubrics.append(rubric)
    return rubrics


async def serialize_trace(run_id: str, db: Any) -> str:
    """Fetch spans for a run and return a compact JSON string."""
    result = await db.execute(
        text("SELECT name, kind, attributes FROM spans WHERE run_id = :run_id ORDER BY started_at ASC"),
        {"run_id": run_id},
    )
    rows = result.fetchall()
    spans = []
    for row in rows:
        attrs = json.loads(row.attributes) if row.attributes else {}
        spans.append({"name": row.name, "kind": row.kind, "attributes": attrs})
    return json.dumps(spans, separators=(",", ":"))


async def call_judge(rubric: dict, trace_json: str) -> tuple[bool, str]:
    """Call Claude-as-judge and return (passed, reasoning)."""
    client = anthropic.AsyncAnthropic()
    prompt = rubric["judge_prompt"].format(trace_json=trace_json)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    try:
        parsed = json.loads(raw)
        return bool(parsed["pass"]), str(parsed.get("reasoning", ""))
    except (json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"Judge returned unparseable response: {raw!r}") from exc


async def run_evals_for_run(
    run_id: str,
    rubrics_dir: str | None = None,
) -> None:
    """Load rubrics, call Claude-as-judge for each, store results in evals table."""
    if rubrics_dir is None:
        rubrics_dir = os.getenv("RUBRICS_DIR", "./rubrics")

    rubrics = load_rubrics(rubrics_dir)
    if not rubrics:
        return

    async with db_module.AsyncSessionLocal() as db:
        trace_json = await serialize_trace(run_id, db)

        for rubric in rubrics:
            eval_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # Insert row with status=running
            await db.execute(
                text(
                    "INSERT INTO evals (eval_id, run_id, rubric_name, status, reasoning, created_at, completed_at) "
                    "VALUES (:eval_id, :run_id, :rubric_name, 'running', NULL, :created_at, NULL)"
                ),
                {"eval_id": eval_id, "run_id": run_id, "rubric_name": rubric["name"], "created_at": now},
            )
            await db.commit()

            try:
                passed, reasoning = await call_judge(rubric, trace_json)
                status = "pass" if passed else "fail"
            except Exception as exc:
                status = "error"
                reasoning = str(exc)

            completed_at = datetime.now(timezone.utc).isoformat()
            await db.execute(
                text(
                    "UPDATE evals SET status = :status, reasoning = :reasoning, completed_at = :completed_at "
                    "WHERE eval_id = :eval_id"
                ),
                {
                    "status": status,
                    "reasoning": reasoning,
                    "completed_at": completed_at,
                    "eval_id": eval_id,
                },
            )
            await db.commit()
