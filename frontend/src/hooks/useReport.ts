import { useCallback, useEffect, useState } from "react"
import { api, type Report } from "@/api/client"

export function useReport() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<"generate" | "run" | null>(null)

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
        await api.runReconciliation(seed)
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Reconciliation failed")
      } finally {
        setBusyAction(null)
      }
    },
    [load]
  )

  const generate = useCallback(
    async (seed?: number) => {
      setBusyAction("generate")
      try {
        await api.generateData(seed)
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Generate failed")
      } finally {
        setBusyAction(null)
      }
    },
    [load]
  )

  return { report, loading, error, busyAction, runReconciliation, generate, reload: load }
}