import { useCallback, useEffect, useState } from "react"
import { api, type ExceptionRecord } from "@/api/client"

export type MakerAction = "confirm" | "reject" | "override"

export interface PendingSelection {
  id: number
  name: string
}

export function useExceptions() {
  const [open, setOpen] = useState<ExceptionRecord[]>([])
  const [pending, setPending] = useState<ExceptionRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set())

  const load = useCallback(async () => {
    try {
      setError(null)
      const [openRows, pRows] = await Promise.all([
        api.exceptions("open"),
        api.pendingApproval(),
      ])
      setOpen(openRows)
      setPending(pRows)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load exceptions")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  /** Maker proposes a resolution for one exception. */
  const resolve = useCallback(
    async (id: number, makerId: string, action: MakerAction, resolutionData?: Record<string, unknown>) => {
      setBusyIds((s) => new Set(s).add(id))
      setError(null)
      try {
        await api.resolve(id, { maker_id: makerId, action, resolution_data: resolutionData })
        await load()
        return true
      } catch (e) {
        setError(e instanceof Error ? e.message : "Resolve failed")
        return false
      } finally {
        setBusyIds((s) => {
          const next = new Set(s)
          next.delete(id)
          return next
        })
      }
    },
    [load]
  )

  /** Checker approves (closes) or rejects (re-opens) a maker proposal. */
  const approve = useCallback(
    async (id: number, checkerId: string, decision: boolean, reasonText?: string) => {
      setBusyIds((s) => new Set(s).add(id))
      setError(null)
      try {
        await api.approve(id, { checker_id: checkerId, decision, reason_text: reasonText })
        await load()
        return true
      } catch (e) {
        setError(e instanceof Error ? e.message : "Approval failed")
        return false
      } finally {
        setBusyIds((s) => {
          const next = new Set(s)
          next.delete(id)
          return next
        })
      }
    },
    [load]
  )

  /** Bulk resolve N exceptions with the same action + maker id (client-side loop). */
  const resolveMany = useCallback(
    async (ids: number[], makerId: string, action: MakerAction) => {
      setBusyIds((s) => new Set([...s, ...ids]))
      setError(null)
      let ok = true
      try {
        for (const id of ids) {
          await api.resolve(id, { maker_id: makerId, action })
        }
        await load()
      } catch (e) {
        setError(e instanceof Error ? e.message : "Bulk resolve failed")
        ok = false
      } finally {
        setBusyIds((s) => {
          const next = new Set(s)
          next.forEach((i) => {
            if (ids.includes(i)) next.delete(i)
          })
          return next
        })
      }
      return ok
    },
    [load]
  )

  return { open, pending, loading, error, busyIds, resolve, approve, resolveMany, reload: load }
}