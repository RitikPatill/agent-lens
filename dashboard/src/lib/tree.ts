import type { Span } from '../types'

/**
 * Returns a map from parent_span_id → child spans.
 * Key null = root-level spans (parent_span_id is null).
 * Keys that are span IDs = children of that span.
 */
export function buildChildMap(spans: Span[]): Map<string | null, Span[]> {
  const map = new Map<string | null, Span[]>()
  for (const span of spans) {
    const key = span.parent_span_id
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(span)
  }
  return map
}

/**
 * Returns the set of span IDs that form the subtree rooted at spanId
 * (inclusive of spanId itself).
 */
export function getSubtreeIds(spanId: string, spans: Span[]): Set<string> {
  const childMap = buildChildMap(spans)
  const result = new Set<string>()

  function dfs(id: string) {
    result.add(id)
    const children = childMap.get(id) ?? []
    for (const child of children) {
      dfs(child.span_id)
    }
  }

  dfs(spanId)
  return result
}
