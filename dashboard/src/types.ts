export type SpanKind = 'llm' | 'tool' | 'agent' | 'memory' | 'retry'
export type RunStatus = 'running' | 'completed' | 'failed'

export interface Run {
  run_id: string
  name: string
  status: RunStatus
  started_at: string
  ended_at: string | null
  root_span_id: string | null
  metadata: Record<string, unknown>
}

export interface Span {
  span_id: string
  run_id: string
  parent_span_id: string | null
  name: string
  kind: SpanKind
  started_at: string
  ended_at: string | null
  attributes: Record<string, unknown>
}

export interface TraceEvent {
  event_type: 'run_start' | 'run_end' | 'span_start' | 'span_end'
  run: Run | null
  span: Span | null
}

export const KIND_COLORS: Record<SpanKind, string> = {
  llm: 'bg-blue-500',
  tool: 'bg-orange-500',
  agent: 'bg-purple-500',
  memory: 'bg-green-500',
  retry: 'bg-red-500',
}
