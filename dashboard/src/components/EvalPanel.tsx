import type { Eval, EvalStatus } from '../types'

const STATUS_STYLES: Record<EvalStatus, string> = {
  pass: 'bg-green-700 text-green-100',
  fail: 'bg-red-700 text-red-100',
  running: 'bg-yellow-700 text-yellow-100',
  pending: 'bg-zinc-600 text-zinc-200',
  error: 'bg-orange-700 text-orange-100',
}

interface EvalPanelProps {
  evals: Eval[]
}

export default function EvalPanel({ evals }: EvalPanelProps) {
  if (evals.length === 0) return null

  return (
    <div className="mt-6">
      <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide mb-2">Eval Results</h2>
      <div className="flex flex-col gap-2">
        {evals.map((e) => (
          <div
            key={e.eval_id}
            className="flex items-center gap-3 bg-zinc-800 rounded px-3 py-2"
            title={e.reasoning ?? undefined}
          >
            <span
              className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${STATUS_STYLES[e.status]}`}
            >
              {e.status.toUpperCase()}
            </span>
            <span className="text-sm text-zinc-200">{e.rubric_name}</span>
            {e.reasoning && (
              <span className="text-xs text-zinc-500 truncate max-w-xs" title={e.reasoning}>
                {e.reasoning}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
