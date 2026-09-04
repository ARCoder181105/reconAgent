import { type Candidate } from "@/api/client"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

/** Map a canonical reason code to a human label + tone. */
export const REASON_LABELS: Record<string, string> = {
  NO_CANDIDATE: "No candidate",
  MULTIPLE_CANDIDATES: "Ambiguous",
  AMOUNT_MISMATCH: "Amount off",
  UTR_UNRESOLVED: "UTR unresolvable",
  DATE_OUT_OF_WINDOW: "Out of window",
  BATCH_PARTITION_AMBIGUOUS: "Batch split",
}

export function reasonTone(reason: string): "amber" | "destructive" | "safe" | "review" | "secondary" {
  switch (reason) {
    case "NO_CANDIDATE":
      return "destructive"
    case "MULTIPLE_CANDIDATES":
    case "BATCH_PARTITION_AMBIGUOUS":
      return "amber"
    case "AMOUNT_MISMATCH":
    case "DATE_OUT_OF_WINDOW":
    case "UTR_UNRESOLVED":
      return "review"
    default:
      return "secondary"
  }
}

export function reasonLabel(reason: string): string {
  return REASON_LABELS[reason] ?? reason
}

/** Format a confidence value against the canonical tiers. */
export function tierLabel(confidence: number | null | undefined): string {
  if (confidence == null) return "—"
  if (confidence >= 85) return "auto"
  if (confidence >= 60) return "review"
  return "hard"
}

export function CandidatesList({
  candidates,
  compact = false,
}: {
  candidates: Candidate[]
  compact?: boolean
}) {
  if (candidates.length === 0) {
    return <span className="text-xs text-muted-foreground">No ranked candidates</span>
  }
  return (
    <ol className={cn("space-y-1", compact ? "text-xs" : "text-sm")}>
      {candidates.map((c, i) => (
        <li key={`${c.settlement_id}-${c.line_id}-${i}`} className="flex items-center justify-between gap-3">
          <code className="font-mono text-xs">
            {c.settlement_id} <span aria-hidden>→</span> {c.line_id}
          </code>
          <span className="flex items-center gap-2">
            <BadgeGlue stage={c.stage} />
            <span className="font-tabular text-muted-foreground">{(c.score * 100).toFixed(1)}%</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

function BadgeGlue({ stage }: { stage: string }) {
  return <Badge variant="outline" className="font-mono">{stage}</Badge>
}