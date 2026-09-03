import type { Report } from "@/api/client"
import { cn } from "@/lib/utils"

interface StageRailProps {
  report: Report
}

interface Segment {
  key: string
  label: string
  value: number
  total: number
  bar: string
  text: string
}

const STAGES = ["exact", "fuzzy_utr", "amount_date", "batch_sum", "llm_tiebreak"]

export function StageRail({ report }: StageRailProps) {
  const total = report.total_settlements || 1
  const auto = report.auto_matched
  const review = report.review_queue
  const exceptions = report.unmatched_settlements
  const verified = report.verified_count

  const segments: Segment[] = [
    { key: "verified", label: "Books closed", value: verified, total, bar: "bg-[var(--books-safe)]", text: "text-[var(--books-safe)]" },
    { key: "auto", label: "Auto-matched", value: auto, total, bar: "bg-primary", text: "text-foreground" },
    { key: "review", label: "In review", value: review, total, bar: "bg-[var(--books-blue)]", text: "text-foreground" },
    { key: "exception", label: "Exception", value: exceptions, total, bar: "bg-[var(--books-amber)]", text: "text-foreground" },
  ]

  return (
    <div className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">
          Stage → Books
        </h3>
        <p className="text-xs text-muted-foreground">
          match_rate vs verified_rate (decision D6)
        </p>
      </div>

      {/* Ledger rail: each segment is width-proportional to its count. */}
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted" role="img" aria-label="proportion of settlements by stage on the way to closed books">
        {segments.map((s) =>
          s.value > 0 ? (
            <div
              key={s.key}
              className={cn(s.bar, "transition-all duration-500")}
              style={{ width: `${(s.value / total) * 100}%` }}
            />
          ) : null
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        {segments.map((s) => (
          <div key={s.key} className="flex items-center gap-2">
            <span aria-hidden className={cn("h-2 w-2 rounded-full", s.bar)} />
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">{s.label}</p>
              <p className={cn("font-tabular text-sm font-medium", s.text)}>
                {s.value}
                <span className="text-muted-foreground"> · {Math.round((s.value / total) * 100)}%</span>
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Which stages close themselves vs need a human (decision D6). */}
      <div className="mt-5 border-t pt-4">
        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Matches by stage</span>
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden className="h-2 w-2 rounded-full bg-primary" /> auto &ge;85 (closed)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden className="h-2 w-2 rounded-full bg-[var(--books-blue)]" /> review 60–84 (needs Maker)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-1.5 pr-2 font-medium">Stage</th>
                <th className="py-1.5 pr-2 text-right font-medium">Auto</th>
                <th className="py-1.5 pr-2 text-right font-medium">Review</th>
                <th className="py-1.5 text-right font-medium">Total</th>
                <th className="sr-only">trust</th>
              </tr>
            </thead>
            <tbody>
              {STAGES.map((stage) => {
                const a = report.by_stage_auto?.[stage] ?? 0
                const r = report.by_stage_review?.[stage] ?? 0
                const n = a + r
                const mixes = a > 0 && r > 0
                return (
                  <tr key={stage} className="border-b border-border/60 last:border-0">
                    <td className="py-1.5 pr-2 font-mono text-xs text-foreground">
                      {stage}
                      {mixes && (
                        <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                          mixed
                        </span>
                      )}
                    </td>
                    <td className={cn("py-1.5 pr-2 text-right font-tabular", a > 0 && "font-medium text-foreground")}>
                      {a > 0 ? a : "—"}
                    </td>
                    <td className={cn("py-1.5 pr-2 text-right font-tabular", r > 0 && "font-medium text-[var(--books-blue)]")}>
                      {r > 0 ? r : "—"}
                    </td>
                    <td className="py-1.5 text-right font-tabular font-medium text-foreground">{n}</td>
                  </tr>
                )
              })}
              <tr className="font-medium">
                <td className="py-2 pr-2 text-xs text-foreground">Total</td>
                <td className="py-2 pr-2 text-right font-tabular text-primary">{report.auto_matched}</td>
                <td className="py-2 pr-2 text-right font-tabular text-[var(--books-blue)]">{report.review_queue}</td>
                <td className="py-2 text-right font-tabular">{report.matched_settlements}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}