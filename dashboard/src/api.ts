import type { Run, Span } from './types'

async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function getRuns(): Promise<Run[]> {
  return apiFetch<Run[]>('/v1/runs')
}

export async function getSpans(runId: string): Promise<Span[]> {
  return apiFetch<Span[]>(`/v1/runs/${runId}/spans`)
}
