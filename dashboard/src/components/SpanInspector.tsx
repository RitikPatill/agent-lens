import { useState } from 'react'
import { X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { Span } from '../types'
import { getSubtreeIds } from '../lib/tree'

interface SpanInspectorProps {
  span: Span
  allSpans: Span[]
  onClose: () => void
}

type Tab = 'Input' | 'Output' | 'Metadata' | 'Raw'

function formatMs(span: Span): string {
  if (!span.ended_at) return 'running…'
  return `${Date.parse(span.ended_at) - Date.parse(span.started_at)}ms`
}

function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}

function PrettyJson({ value }: { value: unknown }) {
  return (
    <pre className="text-xs overflow-auto bg-zinc-900 rounded p-3 text-zinc-200">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

export default function SpanInspector({ span, allSpans, onClose }: SpanInspectorProps) {
  const [activeTab, setActiveTab] = useState<Tab>('Input')
  const tabs: Tab[] = ['Input', 'Output', 'Metadata', 'Raw']

  const subtreeIds = getSubtreeIds(span.span_id, allSpans)
  const subtreeSpans = allSpans.filter((s) => subtreeIds.has(s.span_id))
  const subtreeInputTokens = subtreeSpans.reduce(
    (acc, s) => acc + (typeof s.attributes.input_tokens === 'number' ? s.attributes.input_tokens : 0),
    0
  )
  const subtreeOutputTokens = subtreeSpans.reduce(
    (acc, s) => acc + (typeof s.attributes.output_tokens === 'number' ? s.attributes.output_tokens : 0),
    0
  )

  function renderTab() {
    switch (activeTab) {
      case 'Input': {
        const input = span.attributes.input
        if (typeof input === 'string') {
          return <MarkdownBlock content={input} />
        }
        const messages = span.attributes.messages
        if (messages !== undefined) {
          return <PrettyJson value={messages} />
        }
        return <p className="text-zinc-500 text-sm">No input recorded.</p>
      }
      case 'Output': {
        const output = span.attributes.output
        if (typeof output === 'string') {
          return <MarkdownBlock content={output} />
        }
        return <p className="text-zinc-500 text-sm">No output recorded.</p>
      }
      case 'Metadata': {
        const rows: [string, string][] = [
          ['Kind', span.kind],
          ['Model', typeof span.attributes.model === 'string' ? span.attributes.model : '—'],
          ['Latency', formatMs(span)],
          ['Input tokens', span.attributes.input_tokens != null ? String(span.attributes.input_tokens) : '—'],
          ['Output tokens', span.attributes.output_tokens != null ? String(span.attributes.output_tokens) : '—'],
          ['Subtree input tokens', subtreeInputTokens > 0 ? String(subtreeInputTokens) : '—'],
          ['Subtree output tokens', subtreeOutputTokens > 0 ? String(subtreeOutputTokens) : '—'],
        ]
        return (
          <table className="w-full text-sm">
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={label} className="border-b border-zinc-800">
                  <td className="py-1 pr-4 text-zinc-400 whitespace-nowrap">{label}</td>
                  <td className="py-1 text-zinc-200">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      }
      case 'Raw': {
        return (
          <pre className="text-xs overflow-auto bg-zinc-900 rounded p-3 text-zinc-200">
            {JSON.stringify(span.attributes, null, 2)}
          </pre>
        )
      }
    }
  }

  return (
    <div className="mt-4 pt-4 border-t border-zinc-700">
      {/* header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-zinc-200 truncate" title={span.name}>
          {span.name}
        </h2>
        <button
          className="text-zinc-500 hover:text-zinc-200 ml-2 shrink-0"
          onClick={onClose}
          aria-label="Close inspector"
        >
          <X size={16} />
        </button>
      </div>

      {/* tabs */}
      <div className="flex gap-1 mb-3 border-b border-zinc-700">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`px-3 py-1 text-xs rounded-t transition-colors ${
              activeTab === tab
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* tab content */}
      <div className="overflow-auto max-h-64">{renderTab()}</div>
    </div>
  )
}
