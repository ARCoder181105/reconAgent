import { useAudit } from "@/hooks/useAudit"
import { useLiveSync } from "@/hooks/useLiveSync"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { CheckCircle2, AlertTriangle } from "lucide-react"

const STAGES = ["all", "exact", "fuzzy_utr", "amount_date", "batch_sum", "llm_tiebreak"] as const

const STAGE_TONE: Record<string, "safe" | "review" | "amber" | "secondary" | "outline"> = {
  exact: "safe",
  fuzzy_utr: "secondary",
  amount_date: "review",
  batch_sum: "amber",
  llm_tiebreak: "outline",
}

export function AuditTrail() {
  const { rows, loading, error, stage, minConf, setStageFilter, setConfFilter, resetFilters, reload } = useAudit()
  useLiveSync(reload)

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Every closed pairing
        </p>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
          Audit trail
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          All matched settlement ↔ bank-line pairs, filterable by pipeline stage and confidence —
          including the auto-closed ones, so a reviewer can spot-check what the engine trusted
          on its own.
        </p>
      </header>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1">
          {STAGES.map((s) => (
            <Button
              key={s}
              size="sm"
              variant={stage === (s === "all" ? undefined : s) ? "default" : "outline"}
              onClick={() => setStageFilter(s)}
            >
              {s}
            </Button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">Min conf</span>
          <Input
            type="number"
            min={0}
            max={100}
            className="w-24"
            value={minConf ?? ""}
            placeholder="60"
            onChange={(e) => setConfFilter(Number(e.target.value))}
          />
          <Button size="sm" variant="ghost" onClick={resetFilters}>
            Reset
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
          {error}
        </div>
      )}

      <div className="rounded-lg border bg-card shadow-sm">
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
                <TableHead>Stage</TableHead>
                <TableHead>Settlement</TableHead>
                <TableHead>Bank line</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead>Net</TableHead>
                <TableHead>Resolved</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                    No matches for these filters. Run reconciliation first.
                  </TableCell>
                </TableRow>
              )}
              {rows.map((m) => (
                <TableRow key={m.match_id}>
                  <TableCell>
                    <Badge variant={STAGE_TONE[m.stage] ?? "secondary"} className="font-mono">
                      {m.stage}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{m.settlement_id}</TableCell>
                  <TableCell className="font-mono text-xs">{m.line_id}</TableCell>
                  <TableCell className="text-right">
                    <span className="font-tabular">{m.confidence}</span>
                  </TableCell>
                  <TableCell>
                    {m.net_ok ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-label="Fee math OK" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-amber-500" aria-label="Fee mismatch" />
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{m.resolved_at}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}