import { describe, it, expect } from 'vitest'
import { getSubtreeIds, buildChildMap } from '../lib/tree'
import type { Span } from '../types'

function makeSpan(id: string, parentId: string | null): Span {
  return {
    span_id: id,
    run_id: 'r1',
    parent_span_id: parentId,
    name: id,
    kind: 'agent',
    started_at: '2024-01-01T00:00:00.000Z',
    ended_at: '2024-01-01T00:00:01.000Z',
    attributes: {},
  }
}

const root = makeSpan('root', null)
const child1 = makeSpan('child1', 'root')
const child2 = makeSpan('child2', 'root')
const grandchild = makeSpan('grandchild', 'child1')

const spans = [root, child1, child2, grandchild]

describe('getSubtreeIds', () => {
  it('returns only the target span when it has no children', () => {
    const ids = getSubtreeIds('grandchild', spans)
    expect(ids).toEqual(new Set(['grandchild']))
  })

  it('returns all descendants transitively', () => {
    const ids = getSubtreeIds('root', spans)
    expect(ids).toEqual(new Set(['root', 'child1', 'child2', 'grandchild']))
  })

  it('returns only direct subtree, not siblings', () => {
    const ids = getSubtreeIds('child1', spans)
    expect(ids).toEqual(new Set(['child1', 'grandchild']))
    expect(ids.has('child2')).toBe(false)
  })
})

describe('buildChildMap', () => {
  it('groups spans by parent_span_id', () => {
    const map = buildChildMap(spans)
    expect(map.get(null)).toEqual([root])
    const rootChildren = map.get('root')!
    expect(rootChildren.map((s) => s.span_id).sort()).toEqual(['child1', 'child2'])
    expect(map.get('child1')).toEqual([grandchild])
  })

  it('returns empty map for empty input', () => {
    const map = buildChildMap([])
    expect(map.size).toBe(0)
  })
})
