import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { getRuns } from '../api'
import { useSSE } from '../hooks/useSSE'
import StatusBadge from '../components/StatusBadge'
import type { Run, TraceEvent } from '../types'

function formatDuration(run: Run): string {
  if (!run.ended_at) return '—'
  const ms = Date.parse(run.ended_at) - Date.parse(run.started_at)
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function RunList() {
  const [runs, setRuns] = useState<Run[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .catch((e: Error) => setError(e.message))
  }, [])

  const onEvent = useCallback((e: TraceEvent) => {
    if (e.event_type === 'run_start' && e.run) {
      setRuns((prev) => {
        const exists = prev.some((r) => r.run_id === e.run!.run_id)
        if (exists) return prev
        return [e.run!, ...prev]
      })
    } else if (e.event_type === 'run_end' && e.run) {
      setRuns((prev) =>
        prev.map((r) => (r.run_id === e.run!.run_id ? { ...r, ...e.run! } : r))
      )
    }
  }, [])

  useSSE(onEvent)

  if (error) {
    return <p className="text-red-400">Failed to load runs: {error}</p>
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">Runs</h1>
      {runs.length === 0 ? (
        <p className="text-zinc-500 text-sm">No runs yet. Start an instrumented agent to see traces here.</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left text-zinc-400 border-b border-zinc-800">
              <th className="pb-2 pr-4 font-medium">Status</th>
              <th className="pb-2 pr-4 font-medium">Name</th>
              <th className="pb-2 pr-4 font-medium">Started</th>
              <th className="pb-2 pr-4 font-medium">Duration</th>
              <th className="pb-2 pr-4 font-medium">Model</th>
              <th className="pb-2 font-medium">Tokens</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id} className="border-b border-zinc-800/50 hover:bg-zinc-900/50">
                <td className="py-2 pr-4">
                  <StatusBadge status={run.status} />
                </td>
                <td className="py-2 pr-4">
                  <Link
                    to={`/runs/${run.run_id}`}
                    className="text-blue-400 hover:text-blue-300 hover:underline"
                  >
                    {run.name}
                  </Link>
                </td>
                <td className="py-2 pr-4 text-zinc-400">
                  {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                </td>
                <td className="py-2 pr-4 text-zinc-400">{formatDuration(run)}</td>
                <td className="py-2 pr-4 text-zinc-400">
                  {(run.metadata.model as string) ?? '—'}
                </td>
                <td className="py-2 text-zinc-400">
                  {run.metadata.total_tokens != null
                    ? String(run.metadata.total_tokens)
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
