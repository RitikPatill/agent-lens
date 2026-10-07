import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getRuns, getSpans } from '../api'

function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Internal Server Error',
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('getRuns', () => {
  it('calls /v1/runs and returns the array', async () => {
    const runs = [{ run_id: 'r1', name: 'test', status: 'completed' }]
    globalThis.fetch = mockFetch(runs)

    const result = await getRuns()
    expect(fetch).toHaveBeenCalledWith('/v1/runs')
    expect(result).toEqual(runs)
  })

  it('throws on HTTP 500', async () => {
    globalThis.fetch = mockFetch({}, 500)
    await expect(getRuns()).rejects.toThrow('HTTP 500')
  })
})

describe('getSpans', () => {
  it('calls /v1/runs/:id/spans and returns the array', async () => {
    const spans = [{ span_id: 's1', run_id: 'r1', name: 'llm call', kind: 'llm' }]
    globalThis.fetch = mockFetch(spans)

    const result = await getSpans('r1')
    expect(fetch).toHaveBeenCalledWith('/v1/runs/r1/spans')
    expect(result).toEqual(spans)
  })

  it('throws on HTTP 500', async () => {
    globalThis.fetch = mockFetch({}, 500)
    await expect(getSpans('r1')).rejects.toThrow('HTTP 500')
  })
})
