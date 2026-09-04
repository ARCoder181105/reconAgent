import { useEffect, useRef } from "react"

type Callback = () => void

const listeners = new Set<Callback>()

let source: EventSource | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function connect() {
  if (source && source.readyState !== EventSource.CLOSED) return

  source = new EventSource("/api/events")

  source.onmessage = () => {
    // any event → re-fetch everything that's listening
    for (const cb of listeners) cb()
  }

  source.onerror = () => {
    source?.close()
    source = null
    // EventSource auto-reconnects, but if the server is fully down we back off
    reconnectTimer = setTimeout(connect, 3000)
  }

  source.onopen = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }
}

/**
 * Subscribe to the SSE live-sync stream.  Every mutation on the backend
 * (run-reconciliation, resolve, approve) pushes an event; the registered
 * callback is invoked so the hook can re-fetch its data.
 *
 * Usage:
 *   const { report, reload } = useReport()
 *   useLiveSync(reload)          // ← instantly updates when something changes
 */
export function useLiveSync(callback: Callback) {
  const cbRef = useRef(callback)
  cbRef.current = callback

  useEffect(() => {
    const wrapped = () => cbRef.current()
    listeners.add(wrapped)
    connect() // ensure the shared EventSource is open

    return () => {
      listeners.delete(wrapped)
      // if nobody is listening, tear down the connection
      if (listeners.size === 0 && source) {
        source.close()
        source = null
      }
    }
  }, [])
}
