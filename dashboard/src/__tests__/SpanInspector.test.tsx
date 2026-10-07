import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SpanInspector from '../components/SpanInspector'
import type { Span } from '../types'

// Mock react-markdown to avoid ESM issues in jsdom test environment
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}))

function makeSpan(overrides: Partial<Span> = {}): Span {
  return {
    span_id: 's1',
    run_id: 'r1',
    parent_span_id: null,
    name: 'test-span',
    kind: 'llm',
    started_at: '2024-01-01T00:00:00.000Z',
    ended_at: '2024-01-01T00:00:01.500Z',
    attributes: {},
    ...overrides,
  }
}

describe('SpanInspector', () => {
  it('renders all four tab labels', () => {
    render(<SpanInspector span={makeSpan()} allSpans={[]} onClose={() => {}} />)
    expect(screen.getByText('Input')).toBeInTheDocument()
    expect(screen.getByText('Output')).toBeInTheDocument()
    expect(screen.getByText('Metadata')).toBeInTheDocument()
    expect(screen.getByText('Raw')).toBeInTheDocument()
  })

  it('clicking Raw tab shows JSON of attributes', () => {
    const attrs = { model: 'claude-3', input_tokens: 42 }
    const span = makeSpan({ attributes: attrs })
    render(<SpanInspector span={span} allSpans={[span]} onClose={() => {}} />)
    fireEvent.click(screen.getByText('Raw'))
    expect(screen.getByText(/claude-3/)).toBeInTheDocument()
    expect(screen.getByText(/input_tokens/)).toBeInTheDocument()
  })

  it('Metadata tab shows latency', () => {
    const span = makeSpan({
      started_at: '2024-01-01T00:00:00.000Z',
      ended_at: '2024-01-01T00:00:01.500Z',
    })
    render(<SpanInspector span={span} allSpans={[span]} onClose={() => {}} />)
    fireEvent.click(screen.getByText('Metadata'))
    expect(screen.getByText('1500ms')).toBeInTheDocument()
  })

  it('Input tab renders when span.attributes.input is present', () => {
    const span = makeSpan({ attributes: { input: 'Hello from agent' } })
    render(<SpanInspector span={span} allSpans={[span]} onClose={() => {}} />)
    // Input tab is active by default
    expect(screen.getByTestId('markdown')).toBeInTheDocument()
    expect(screen.getByText('Hello from agent')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<SpanInspector span={makeSpan()} allSpans={[]} onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('Close inspector'))
    expect(onClose).toHaveBeenCalled()
  })

  it('Output tab shows no output message when absent', () => {
    render(<SpanInspector span={makeSpan()} allSpans={[]} onClose={() => {}} />)
    fireEvent.click(screen.getByText('Output'))
    expect(screen.getByText('No output recorded.')).toBeInTheDocument()
  })
})
