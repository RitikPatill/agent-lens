# AgentLens Roadmap

Near-term and medium-term extensions. Each item notes why it's valuable and roughly how it would be implemented.

---

## OpenTelemetry export

**Why:** Teams running AgentLens alongside an existing observability stack (Jaeger, Grafana Tempo, Honeycomb) want to correlate agent traces with infrastructure metrics without duplicating storage.

**How:** Add `server/agentlens_server/otlp_exporter.py` that maps AgentLens `spans` rows to OTLP `ResourceSpans` protobuf and flushes them to a configurable OTLP endpoint after each run completes. Expose an `--otlp <endpoint>` flag on `agentlens serve`. The existing schema maps cleanly: `run_id` → trace ID, `span_id` → span ID, `parent_span_id` → parent span ID, `kind` → OTel span kind, `attributes` → OTel attributes.

---

## Framework adapters

**Why:** Users of LangChain, LangGraph, and CrewAI shouldn't have to manually add `@traced` and `span()` calls — AgentLens should integrate at the framework's native extension points.

**How:**
- `agentlens.langchain` — implement a `BaseCallbackHandler` that maps `on_llm_start`/`on_llm_end`/`on_tool_start`/`on_tool_end` to AgentLens span open/close calls.
- `agentlens.langgraph` — wrap each node function with `@traced(kind=SpanKind.agent)` at graph-build time using LangGraph's node middleware API.
- `agentlens.crewai` — subclass `Task` to inject `span()` context managers around task execution.

No new SDK internals are required; each adapter is a thin translation layer on top of the existing `@traced` + `span()` primitives.

---

## Dataset-based regression evals

**Why:** Ad-hoc rubric evals catch qualitative regressions, but engineers also need to know "did my prompt change break the 20 golden test cases I curated last sprint?"

**How:** Add a `datasets` table holding (input, expected_output, run_id) triples captured from production or hand-written. Add a `agentlens replay <dataset>` CLI command that re-runs each input through the agent, records a new trace, and diffs the rubric scores against the baseline run. Surface a "regression dashboard" view showing score deltas across dataset entries.

---

## Prompt diff view

**Why:** Prompt engineering is iterative. Comparing the exact prompt sent in run A vs run B side-by-side is faster than hunting through two separate span inspectors.

**How:** Add a `/runs/compare?a=<run_id>&b=<run_id>` dashboard route. For each matching span name, render a two-column diff (using a JS diffing library such as `diff` or `monaco-editor`'s diff mode) of the `input` attribute. Token count deltas and latency deltas shown inline.

---

## Cost tracking

**Why:** Token costs add up quickly in multi-agent systems. Developers need per-run and per-span USD cost visibility to catch runaway agents before the billing cycle.

**How:** Add a `pricing.json` to the server with per-model input/output token prices (updated from Anthropic's pricing page). In `db.py`, compute `cost_usd` on every `llm` span write and roll it up to the `runs` table. Surface cost in the dashboard's run list column and span inspector metadata tab.

---

## Packaging

**Why:** `pip install agentlens` should just work without cloning the repo.

**How:**
- Publish `agentlens` (SDK only) to PyPI — no server dependencies, minimal footprint.
- Add `agentlens[server]` extra that pulls in `fastapi`, `sqlalchemy[asyncio]`, `uvicorn`, `aiofiles`, and `anthropic` so users can run `agentlens serve` from a single install.
- Add a `agentlens` CLI entry point (`__main__.py`) with `serve`, `replay`, and `version` subcommands.
- Set up GitHub Actions to publish on tag push.
