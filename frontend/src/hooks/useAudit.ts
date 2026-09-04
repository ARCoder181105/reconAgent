import { useCallback, useEffect, useState } from "react"
import { api, type Match } from "@/api/client"

export function useAudit() {
  const [rows, setRows] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<string | undefined>(undefined)
  const [minConf, setMinConf] = useState<number | undefined>(undefined)

  const load = useCallback(async () => {
    try {
      setError(null)
      setRows(await api.matches(stage, minConf))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load matches")
    } finally {
      setLoading(false)
    }
  }, [stage, minConf])

  useEffect(() => {
    void load()
  }, [load])

  const setStageFilter = (s: string) => setStage(s === "all" ? undefined : s)
  const setConfFilter = (c: number) => setMinConf(c)
  const resetFilters = () => {
    setStage(undefined)
    setMinConf(undefined)
  }

  return { rows, loading, error, stage, minConf, setStageFilter, setConfFilter, resetFilters, reload: load }
}