import { useCallback, useEffect, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { api, type BankStatement, type Settlement } from "@/api/client"
import { useLiveSync } from "@/hooks/useLiveSync"
import { formatINR, formatINRDecimal } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"

const PAGE = 20

export function Inspection() {
  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Raw input
        </p>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
          Data inspection
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The messy, un-reconciled source records the engine works from. Settlements carry integer paise; statement lines carry rupee floats.
        </p>
      </header>
      <SettlementsSection />
      <StatementSection />
    </div>
  )
}

function SettlementsSection() {
  const [rows, setRows] = useState<Settlement[]>([])
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (off: number) => {
    setLoading(true)
    setError(null)
    try {
      setRows(await api.settlements(PAGE, off))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settlements")
    } finally {
      setLoading(false)
    }
  }, [])

  useLiveSync(() => load(offset))

  useEffect(() => {
    void load(0)
  }, [load])

  const goto = (off: number) => {
    if (off < 0) return
    setOffset(off)
    void load(off)
  }

  return (
    <section aria-label="Settlements">
      <h2 className="font-display text-lg font-semibold tracking-tight text-foreground">Settlements</h2>
      <div className="mt-2 rounded-lg border bg-card shadow-sm">
        {error && <p className="p-4 text-sm text-destructive">{error}</p>}
        {loading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>UTR</TableHead>
                <TableHead className="text-right">Net (paise)</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((s) => (
                <TableRow key={s.settlement_id}>
                  <TableCell className="font-mono text-xs">{s.settlement_id}</TableCell>
                  <TableCell className="font-mono text-xs">{s.utr ?? "—"}</TableCell>
                  <TableCell className="font-tabular text-right">{formatINR(s.net_amount)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{s.settlement_date ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono">{s.status ?? "—"}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {!loading && (
          <div className="flex items-center justify-end gap-2 border-t px-4 py-2">
            <Button variant="ghost" size="sm" onClick={() => goto(offset - PAGE)} disabled={offset === 0}>
              <ChevronLeft className="h-4 w-4" /> Prev
            </Button>
            <span className="text-xs text-muted-foreground font-tabular">rows {offset + 1}–{offset + rows.length}</span>
            <Button variant="ghost" size="sm" onClick={() => goto(offset + PAGE)} disabled={rows.length < PAGE}>
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}

function StatementSection() {
  const [rows, setRows] = useState<BankStatement[]>([])
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (off: number) => {
    setLoading(true)
    setError(null)
    try {
      setRows(await api.bankStatement(PAGE, off))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load statement")
    } finally {
      setLoading(false)
    }
  }, [])

  useLiveSync(() => load(offset))

  useEffect(() => {
    void load(0)
  }, [load])

  const goto = (off: number) => {
    if (off < 0) return
    setOffset(off)
    void load(off)
  }

  return (
    <section aria-label="Bank statement">
      <h2 className="font-display text-lg font-semibold tracking-tight text-foreground">Bank statement</h2>
      <div className="mt-2 rounded-lg border bg-card shadow-sm">
        {error && <p className="p-4 text-sm text-destructive">{error}</p>}
        {loading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Line</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Description / Ref</TableHead>
                <TableHead className="text-right">Credit</TableHead>
                <TableHead className="text-right">Debit</TableHead>
                <TableHead className="text-right">Balance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((b) => (
                <TableRow key={b.line_id}>
                  <TableCell className="font-mono text-xs">{b.line_id}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{b.txn_date ?? b.value_date ?? "—"}</TableCell>
                  <TableCell className="max-w-[18rem] truncate text-xs text-foreground" title={b.description ?? ""}>
                    {b.description ?? b.ref_no ?? "—"}
                  </TableCell>
                  <TableCell className="font-tabular text-right text-[var(--books-safe)]">
                    {b.credit != null ? formatINRDecimal(b.credit) : "—"}
                  </TableCell>
                  <TableCell className="font-tabular text-right text-destructive">
                    {b.debit != null ? formatINRDecimal(b.debit) : "—"}
                  </TableCell>
                  <TableCell className="font-tabular text-right text-muted-foreground">
                    {formatINRDecimal(b.balance)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {!loading && (
          <div className="flex items-center justify-end gap-2 border-t px-4 py-2">
            <Button variant="ghost" size="sm" onClick={() => goto(offset - PAGE)} disabled={offset === 0}>
              <ChevronLeft className="h-4 w-4" /> Prev
            </Button>
            <span className="text-xs text-muted-foreground font-tabular">rows {offset + 1}–{offset + rows.length}</span>
            <Button variant="ghost" size="sm" onClick={() => goto(offset + PAGE)} disabled={rows.length < PAGE}>
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}