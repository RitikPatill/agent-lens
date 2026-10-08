import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { getRuns, getSpans, getEvals } from '../api'
import { useSSE } from '../hooks/useSSE'
import StatusBadge from '../components/StatusBadge'
import GanttChart from '../components/GanttChart'
import CallTree from '../components/CallTree'
import SpanInspector from '../components/SpanInspector'
import EvalPanel from '../components/EvalPanel'
import type { Eval, Run, Span, TraceEvent } from '../types'

function formatDuration(run: Run): string {
  if (!run.ended_at) return 'running…'
  const ms = Date.parse(run.ended_at) - Date.parse(run.started_at)
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [evals, setEvals] = useState<Eval[]>([])
  const [error, setError] = useState<string | null>(null)
  const [, setTick] = useState(0)
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null)
  const evalPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!runId) return
    Promise.all([getRuns(), getSpans(runId), getEvals(runId)])
      .then(([allRuns, fetchedSpans, fetchedEvals]) => {
        const found = allRuns.find((r) => r.run_id === runId) ?? null
        if (!found) {
          setError('Run not found')
          return
        }
        setRun(found)
        setSpans(fetchedSpans)
        setEvals(fetchedEvals)
      })
      .catch((e: Error) => setError(e.message))
  }, [runId])

  // Poll evals every 3s while run is running; stop when all are terminal
  useEffect(() => {
    if (!runId || !run) return
    const TERMINAL = new Set(['pass', 'fail', 'error'])
    const allTerminal = (es: Eval[]) => es.length > 0 && es.every((e) => TERMINAL.has(e.status))

    if (run.status !== 'running' && allTerminal(evals)) return

    if (evalPollRef.current) clearInterval(evalPollRef.current)
    evalPollRef.current = setInterval(() => {
      getEvals(runId)
        .then((fetched) => {
          setEvals(fetched)
          if (run.status !== 'running' && allTerminal(fetched)) {
            clearInterval(evalPollRef.current!)
            evalPollRef.current = null
          }
        })
        .catch(() => {/* ignore poll errors */})
    }, 3000)

    return () => {
      if (evalPollRef.current) clearInterval(evalPollRef.current)
    }
  }, [runId, run?.status])

  // re-render every second while run is live so Gantt bars grow
  useEffect(() => {
    if (!run || run.status !== 'running') return
    const id = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [run?.status])

  const onEvent = useCallback(
    (e: TraceEvent) => {
      if (!runId) return
      if (e.event_type === 'run_end' && e.run?.run_id === runId) {
        setRun((prev) => (prev ? { ...prev, ...e.run! } : prev))
        // Fetch evals once after run completes
        getEvals(runId).then(setEvals).catch(() => {/* ignore */})
      }
      if (e.event_type === 'span_start' && e.span?.run_id === runId) {
        setSpans((prev) => {
          const exists = prev.some((s) => s.span_id === e.span!.span_id)
          return exists ? prev : [...prev, e.span!]
        })
      }
      if (e.event_type === 'span_end' && e.span?.run_id === runId) {
        setSpans((prev) =>
          prev.map((s) => (s.span_id === e.span!.span_id ? { ...s, ...e.span! } : s))
        )
      }
    },
    [runId]
  )

  useSSE(onEvent)

  const selectedSpan = selectedSpanId ? spans.find((s) => s.span_id === selectedSpanId) ?? null : null

  if (error) {
    return (
      <div>
        <Link to="/" className="text-zinc-400 hover:text-zinc-200 text-sm">← Back to runs</Link>
        <p className="mt-4 text-red-400">{error}</p>
      </div>
    )
  }

  if (!run) {
    return (
      <div>
        <Link to="/" className="text-zinc-400 hover:text-zinc-200 text-sm">← Back to runs</Link>
        <p className="mt-4 text-zinc-500 text-sm">Loading…</p>
      </div>
    )
  }

  return (
    <div>
      <Link to="/" className="text-zinc-400 hover:text-zinc-200 text-sm">← Back to runs</Link>

      {/* run header */}
      <div className="mt-4 mb-6">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-xl font-semibold">{run.name}</h1>
          <StatusBadge status={run.status} />
        </div>
        <p className="text-sm text-zinc-400">
          Started {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
          {' · '}
          {formatDuration(run)}
          {run.metadata.model ? ` · ${String(run.metadata.model)}` : ''}
        </p>
      </div>

      {spans.length === 0 ? (
        <p className="text-zinc-500 text-sm">No spans yet.</p>
      ) : (
        <>
          {/* two-column: Gantt left, CallTree right */}
          <div className="grid grid-cols-[1fr_300px] gap-4">
            <GanttChart
              spans={spans}
              runStartedAt={run.started_at}
              selectedSpanId={selectedSpanId}
              onSpanClick={setSelectedSpanId}
            />
            <CallTree
              spans={spans}
              selectedSpanId={selectedSpanId}
              onSelect={setSelectedSpanId}
            />
          </div>

          {/* span inspector panel */}
          {selectedSpan && (
            <SpanInspector
              span={selectedSpan}
              allSpans={spans}
              onClose={() => setSelectedSpanId(null)}
            />
          )}

          <EvalPanel evals={evals} />
        </>
      )}
    </div>
  )
}
