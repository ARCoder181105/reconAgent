import { useCallback, useEffect, useState } from "react"
import { api, type Report } from "@/api/client"

export function useReport() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<"run" | null>(null)
  const [lastSeed, setLastSeed] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await api.report()
      setReport(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const runReconciliation = useCallback(
    async (seed?: number) => {
      setBusyAction("run")
      try {
        // Generate a fresh random dataset, then reconcile it. Pass an explicit
        // random seed so every click produces different data (the backend
        // regenerates from seed and matches — without it, it reuses seed 42 and
        // the board would look frozen at 48/48 every time).
        const effectiveSeed = seed ?? Math.floor(Math.random() * 1e6)
        setLastSeed(effectiveSeed)
        await api.runReconciliation(effectiveSeed)
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Reconciliation failed")
      } finally {
        setBusyAction(null)
      }
    },
    [load]
  )

  return { report, loading, error, busyAction, runReconciliation, lastSeed, reload: load }
}