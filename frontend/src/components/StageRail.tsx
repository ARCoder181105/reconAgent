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

      <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 border-t pt-3 text-xs sm:grid-cols-5">
        {STAGES.map((stage) => {
          const n = report.by_stage?.[stage] ?? 0
          return (
            <div key={stage} className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">{stage}</span>
              <span className="font-tabular font-medium text-foreground">{n}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}