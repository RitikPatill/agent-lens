import { useState } from 'react'
import type { Span } from '../types'
import { KIND_COLORS } from '../types'

interface TooltipInfo {
  span: Span
  x: number
  y: number
}

interface Props {
  spans: Span[]
  runStartedAt: string
  selectedSpanId?: string | null
  onSpanClick?: (spanId: string) => void
}

export default function GanttChart({ spans, runStartedAt, selectedSpanId, onSpanClick }: Props) {
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null)

  const runStart = Date.parse(runStartedAt)
  const now = Date.now()

  const latestEnd = spans.reduce((acc, s) => {
    const end = s.ended_at ? Date.parse(s.ended_at) : now
    return Math.max(acc, end)
  }, runStart)

  const totalMs = Math.max(latestEnd - runStart, 1)

  return (
    <div className="relative overflow-x-auto">
      <div className="min-w-[600px]">
        {/* header */}
        <div className="flex text-xs text-zinc-500 mb-1 pl-[200px]">
          <span>0ms</span>
          <span className="ml-auto">{totalMs}ms</span>
        </div>

        {spans.map((span) => {
          const spanStart = Date.parse(span.started_at)
          const spanEnd = span.ended_at ? Date.parse(span.ended_at) : now
          const offsetPct = ((spanStart - runStart) / totalMs) * 100
          const widthPct = Math.max(((spanEnd - spanStart) / totalMs) * 100, 0.5)
          const isRunning = span.ended_at === null
          const colorClass = KIND_COLORS[span.kind] ?? 'bg-zinc-500'

          const isSelected = span.span_id === selectedSpanId

          return (
            <div key={span.span_id} className="flex items-center mb-1 group">
              {/* label */}
              <div
                className={`w-[200px] shrink-0 pr-2 text-xs truncate cursor-pointer ${isSelected ? 'text-zinc-100' : 'text-zinc-300'}`}
                title={span.name}
                onClick={() => onSpanClick?.(span.span_id)}
              >
                {span.name}
              </div>

              {/* bar track */}
              <div className="flex-1 relative h-5 bg-zinc-800 rounded">
                <div
                  className={`absolute h-full rounded ${colorClass} ${isRunning ? 'animate-pulse' : ''} ${isSelected ? 'ring-2 ring-white' : ''} cursor-pointer`}
                  style={{
                    left: `${offsetPct}%`,
                    width: `${widthPct}%`,
                  }}
                  onClick={() => onSpanClick?.(span.span_id)}
                  onMouseEnter={(e) => setTooltip({ span, x: e.clientX, y: e.clientY })}
                  onMouseLeave={() => setTooltip(null)}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-zinc-800 border border-zinc-700 rounded shadow-lg p-3 text-xs text-zinc-200 pointer-events-none max-w-xs"
          style={{ top: tooltip.y + 12, left: tooltip.x + 12 }}
        >
          <p className="font-semibold mb-1">{tooltip.span.name}</p>
          <p className="text-zinc-400">kind: <span className="text-zinc-200">{tooltip.span.kind}</span></p>
          {tooltip.span.ended_at ? (
            <p className="text-zinc-400">
              duration:{' '}
              <span className="text-zinc-200">
                {Date.parse(tooltip.span.ended_at) - Date.parse(tooltip.span.started_at)}ms
              </span>
            </p>
          ) : (
            <p className="text-amber-400">running…</p>
          )}
          {tooltip.span.attributes.input_tokens != null && (
            <p className="text-zinc-400">
              in tokens: <span className="text-zinc-200">{String(tooltip.span.attributes.input_tokens)}</span>
            </p>
          )}
          {tooltip.span.attributes.output_tokens != null && (
            <p className="text-zinc-400">
              out tokens: <span className="text-zinc-200">{String(tooltip.span.attributes.output_tokens)}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
