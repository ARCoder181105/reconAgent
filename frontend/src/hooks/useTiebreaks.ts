import { useCallback, useEffect, useRef, useState } from "react"
import { api, type TiebreaksStatus } from "@/api/client"

const POLL_MS = 2000

interface UseTiebreaks {
  status: TiebreaksStatus | null
  active: boolean
  error: string | null
  /* Register a callback fired once the queue drains (LLM results may have landed). */
  setOnDone: (cb: (() => void) | null) => void
}

export function useTiebreaks(): UseTiebreaks {
  const [status, setStatus] = useState<TiebreaksStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const onDoneRef = useRef<(() => void) | null>(null)

  const setOnDone = useCallback((cb: (() => void) | null) => {
    onDoneRef.current = cb
  }, [])

  const active = (status?.pending ?? 0) > 0

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setInterval> | null = null

    const tick = async () => {
      try {
        const s = await api.aiTiebreaks()
        if (cancelled) return
        setStatus(s)
        setError(null)
        // When the queue is drained (was active, now zero) notify the parent.
        if (s.pending === 0 && onDoneRef.current) {
          const cb = onDoneRef.current
          onDoneRef.current = null
          cb()
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Tie-break status failed")
      }
    }

    void tick()
    timer = setInterval(tick, POLL_MS)
    return () => {
      cancelled = true
      if (timer) clearInterval(timer)
    }
  }, [])

  return { status, active, error, setOnDone }
}