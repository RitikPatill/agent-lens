import { useEffect, useRef } from 'react'
import type { TraceEvent } from '../types'

export function useSSE(onEvent: (e: TraceEvent) => void): void {
  const cbRef = useRef(onEvent)
  useEffect(() => {
    cbRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    let es: EventSource
    let disconnected = false
    let retryTimeout: ReturnType<typeof setTimeout> | null = null

    function connect() {
      es = new EventSource('/v1/stream')

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as TraceEvent
          cbRef.current(data)
        } catch {
          // ignore malformed events
        }
      }

      es.onerror = () => {
        es.close()
        if (!disconnected) {
          retryTimeout = setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      disconnected = true
      if (retryTimeout) clearTimeout(retryTimeout)
      es?.close()
    }
  }, [])
}
