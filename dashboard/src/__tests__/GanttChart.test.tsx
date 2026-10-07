import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import GanttChart from '../components/GanttChart'
import type { Span } from '../types'

const runStartedAt = '2024-01-01T00:00:00.000Z'

const completedSpan: Span = {
  span_id: 's1',
  run_id: 'r1',
  parent_span_id: null,
  name: 'completed-span',
  kind: 'llm',
  started_at: '2024-01-01T00:00:00.100Z',
  ended_at: '2024-01-01T00:00:01.100Z',
  attributes: { input_tokens: 100, output_tokens: 200 },
}

const runningSpan: Span = {
  span_id: 's2',
  run_id: 'r1',
  parent_span_id: null,
  name: 'running-span',
  kind: 'tool',
  started_at: '2024-01-01T00:00:01.000Z',
  ended_at: null,
  attributes: {},
}

describe('GanttChart', () => {
  it('renders both span names in the DOM', () => {
    render(<GanttChart spans={[completedSpan, runningSpan]} runStartedAt={runStartedAt} />)
    expect(screen.getByText('completed-span')).toBeInTheDocument()
    expect(screen.getByText('running-span')).toBeInTheDocument()
  })

  it('running span bar has animate-pulse class', () => {
    const { container } = render(
      <GanttChart spans={[runningSpan]} runStartedAt={runStartedAt} />
    )
    const bar = container.querySelector('.animate-pulse')
    expect(bar).not.toBeNull()
  })

  it('completed span bar has non-zero width style', () => {
    const { container } = render(
      <GanttChart spans={[completedSpan]} runStartedAt={runStartedAt} />
    )
    // find the colored bar div (has inline style with width)
    const bars = container.querySelectorAll('[style*="width"]')
    expect(bars.length).toBeGreaterThan(0)
    const widthStyle = (bars[0] as HTMLElement).style.width
    const widthValue = parseFloat(widthStyle)
    expect(widthValue).toBeGreaterThan(0)
  })
})
