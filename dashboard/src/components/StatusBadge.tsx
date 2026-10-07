import type { RunStatus } from '../types'

const STATUS_STYLES: Record<RunStatus, string> = {
  running: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  completed: 'bg-green-500/20 text-green-400 border border-green-500/30',
  failed: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

interface Props {
  status: RunStatus
}

export default function StatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status === 'running' && (
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
      )}
      {status}
    </span>
  )
}
