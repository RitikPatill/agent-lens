import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CallTree from '../components/CallTree'
import type { Span } from '../types'

function makeSpan(id: string, parentId: string | null, name?: string): Span {
  return {
    span_id: id,
    run_id: 'r1',
    parent_span_id: parentId,
    name: name ?? id,
    kind: 'agent',
    started_at: '2024-01-01T00:00:00.000Z',
    ended_at: '2024-01-01T00:00:01.000Z',
    attributes: {},
  }
}

const root = makeSpan('root', null, 'Root Span')
const child = makeSpan('child', 'root', 'Child Span')
const grandchild = makeSpan('gc', 'child', 'Grandchild Span')

describe('CallTree', () => {
  it('renders root span name', () => {
    render(<CallTree spans={[root]} selectedSpanId={null} onSelect={() => {}} />)
    expect(screen.getByText('Root Span')).toBeInTheDocument()
  })

  it('children are not visible until root is expanded (root starts expanded)', () => {
    // Root starts expanded (it's a root-level span), so child IS visible initially
    render(<CallTree spans={[root, child]} selectedSpanId={null} onSelect={() => {}} />)
    expect(screen.getByText('Child Span')).toBeInTheDocument()
  })

  it('collapsing root hides children', () => {
    render(<CallTree spans={[root, child]} selectedSpanId={null} onSelect={() => {}} />)
    // Child is visible; click the expand button on root to collapse
    const expandBtns = screen.getAllByRole('button', { name: /collapse/i })
    fireEvent.click(expandBtns[0])
    expect(screen.queryByText('Child Span')).toBeNull()
  })

  it('expanding a collapsed node reveals children', () => {
    // Root starts expanded; child starts collapsed (depth > 0)
    render(<CallTree spans={[root, child, grandchild]} selectedSpanId={null} onSelect={() => {}} />)
    // child is visible (root expanded), but grandchild is hidden (child collapsed)
    expect(screen.queryByText('Grandchild Span')).toBeNull()
    // click the expand button on child
    const expandBtns = screen.getAllByRole('button', { name: /expand/i })
    fireEvent.click(expandBtns[0])
    expect(screen.getByText('Grandchild Span')).toBeInTheDocument()
  })

  it('clicking a span calls onSelect with correct span_id', () => {
    const onSelect = vi.fn()
    render(<CallTree spans={[root, child]} selectedSpanId={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('Child Span'))
    expect(onSelect).toHaveBeenCalledWith('child')
  })

  it('selected span has highlight class', () => {
    const { container } = render(
      <CallTree spans={[root]} selectedSpanId="root" onSelect={() => {}} />
    )
    const highlighted = container.querySelector('.bg-zinc-700')
    expect(highlighted).not.toBeNull()
  })
})
