import { useEffect } from "react"
import { RefreshCw, Play } from "lucide-react"
import { useReport } from "@/hooks/useReport"
import { useTiebreaks } from "@/hooks/useTiebreaks"
import { useLiveSync } from "@/hooks/useLiveSync"
import { MetricCard } from "@/components/MetricCard"
import { StageRail } from "@/components/StageRail"
import { TieBreakIndicator } from "@/components/TieBreakIndicator"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

const rupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
})

export function Dashboard() {
  const { report, loading, error, busyAction, runReconciliation, lastSeed, reload } = useReport()
  const { status, active, error: tieError, setOnDone } = useTiebreaks()

  useLiveSync(reload)

  const pending = status?.pending ?? 0

  // Once the async LLM queue drains, reload the report (results may have landed).
  useEffect(() => {
    setOnDone(() => reload)
  }, [setOnDone, reload])

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Reconciliation overview
          </p>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            How the books reconcile
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {lastSeed != null && (
            <span className="font-mono text-xs text-muted-foreground">
              last run · seed <span className="text-foreground">{lastSeed}</span>
            </span>
          )}
          <Button onClick={() => runReconciliation()} disabled={busyAction === "run"}>
            {busyAction === "run" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {busyAction === "run" ? "Reconciling…" : "Run reconciliation"}
          </Button>
        </div>
      </header>

      {(error || tieError) && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
          {error ?? tieError}
        </div>
      )}

      <TieBreakIndicator
        active={active}
        pending={pending}
        processed={status?.processed ?? 0}
        failed={status?.failed ?? 0}
      />

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : report ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Match rate"
              value={`${report.match_rate.toFixed(1)}%`}
              sub={`${report.auto_matched} of ${report.total_settlements} auto-matched`}
              accent="neutral"
            />
            <MetricCard
              label="Review rate"
              value={`${report.review_rate.toFixed(1)}%`}
              sub={`${report.review_queue} in review band (60–84)`}
              accent="review"
            />
            <MetricCard
              label="Exception rate"
              value={`${report.exception_rate.toFixed(1)}%`}
              sub={`${report.unmatched_settlements} need a human`}
              accent="amber"
            />
            <MetricCard
              label="Verified rate"
              value={`${report.verified_rate.toFixed(1)}%`}
              sub={`${report.verified_count} books closed`}
              accent="safe"
            />
          </div>

          <section aria-label="Cash position">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Cash position · net settlement value
            </p>
            <div className="mt-1 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Auto-matched"
                value={rupees.format(report.cash.rupees_auto)}
                sub="confidence ≥ 85"
                accent="neutral"
              />
              <MetricCard
                label="Review band"
                value={rupees.format(report.cash.rupees_review)}
                sub="60–84 → human"
                accent="review"
              />
              <MetricCard
                label="Exceptions"
                value={rupees.format(report.cash.rupees_exceptions)}
                sub="needs a human"
                accent="amber"
              />
              <MetricCard
                label="Verified"
                value={rupees.format(report.cash.rupees_verified)}
                sub="books closed by checker"
                accent="safe"
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Verified ≤ auto is intent, not a bug: the engine proposes; only a checker closes books (decision D6).
            </p>
          </section>

          <StageRail report={report} />

          <section className="grid gap-6 md:grid-cols-2" aria-label="Supplementary">
            <div className="rounded-lg border bg-card p-5 shadow-sm">
              <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">By reason code</h3>
              {Object.entries(report.by_reason).length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No open exceptions.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {Object.entries(report.by_reason).map(([code, count]) => (
                    <li key={code} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs text-foreground">{code}</span>
                      <span className="font-tabular font-medium text-muted-foreground">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-lg border bg-card p-5 shadow-sm">
              <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">Volume</h3>
              <p className="mt-3 text-sm text-muted-foreground">
                {report.total_settlements} settlements · {report.total_bank_lines} bank lines ·{" "}
                {report.bank_lines_matched} lines matched · {report.verified_count} verified.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                match_rate is an engine signal; verified_rate is books actually closed (decision D6).
              </p>
            </div>
          </section>
        </>
      ) : null}
    </div>
  )
}