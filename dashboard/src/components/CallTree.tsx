import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import type { Span } from '../types'
import { KIND_COLORS } from '../types'
import { buildChildMap } from '../lib/tree'

interface CallTreeProps {
  spans: Span[]
  selectedSpanId: string | null
  onSelect: (spanId: string) => void
}

interface TreeNodeProps {
  span: Span
  childMap: Map<string | null, Span[]>
  depth: number
  expanded: Set<string>
  onToggle: (spanId: string) => void
  selectedSpanId: string | null
  onSelect: (spanId: string) => void
}

function formatDuration(span: Span): string {
  if (!span.ended_at) return '…'
  const ms = Date.parse(span.ended_at) - Date.parse(span.started_at)
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function TreeNode({ span, childMap, depth, expanded, onToggle, selectedSpanId, onSelect }: TreeNodeProps) {
  const children = childMap.get(span.span_id) ?? []
  const hasChildren = children.length > 0
  const isExpanded = expanded.has(span.span_id)
  const isSelected = span.span_id === selectedSpanId
  const colorClass = KIND_COLORS[span.kind] ?? 'bg-zinc-500'
  const dotColor = colorClass.replace('bg-', 'bg-')

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-0.5 px-1 rounded cursor-pointer hover:bg-zinc-700/60 text-xs ${isSelected ? 'bg-zinc-700 ring-1 ring-zinc-500' : ''}`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => onSelect(span.span_id)}
      >
        {/* expand/collapse toggle */}
        <button
          className="w-4 h-4 flex items-center justify-center shrink-0 text-zinc-400 hover:text-zinc-200"
          onClick={(e) => {
            e.stopPropagation()
            if (hasChildren) onToggle(span.span_id)
          }}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {hasChildren ? (
            isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
          ) : (
            <span className="w-3" />
          )}
        </button>

        {/* kind dot */}
        <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />

        {/* name */}
        <span className="text-zinc-200 truncate flex-1" title={span.name}>
          {span.name}
        </span>

        {/* duration */}
        <span className="text-zinc-500 shrink-0 ml-2">{formatDuration(span)}</span>
      </div>

      {hasChildren && isExpanded && children.map((child) => (
        <TreeNode
          key={child.span_id}
          span={child}
          childMap={childMap}
          depth={depth + 1}
          expanded={expanded}
          onToggle={onToggle}
          selectedSpanId={selectedSpanId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}

export default function CallTree({ spans, selectedSpanId, onSelect }: CallTreeProps) {
  const spanIds = new Set(spans.map((s) => s.span_id))
  const roots = spans.filter(
    (s) => s.parent_span_id === null || !spanIds.has(s.parent_span_id)
  )

  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(roots.map((r) => r.span_id))
  )

  const childMap = buildChildMap(spans)

  function onToggle(spanId: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(spanId)) next.delete(spanId)
      else next.add(spanId)
      return next
    })
  }

  if (spans.length === 0) {
    return <p className="text-zinc-500 text-xs p-2">No spans yet.</p>
  }

  return (
    <div className="text-sm font-mono overflow-y-auto max-h-96">
      {roots.map((root) => (
        <TreeNode
          key={root.span_id}
          span={root}
          childMap={childMap}
          depth={0}
          expanded={expanded}
          onToggle={onToggle}
          selectedSpanId={selectedSpanId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}
