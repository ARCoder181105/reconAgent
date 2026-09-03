import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface TieBreakIndicatorProps {
  active: boolean
  pending: number
  processed: number
  failed: number
}

export function TieBreakIndicator({ active, pending, processed, failed }: TieBreakIndicatorProps) {
  if (!active && processed === 0 && failed === 0) return null

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-md border px-3 py-2 text-sm",
        active ? "border-[var(--books-blue)] bg-[var(--books-blue)]/10 text-foreground" : "border-border bg-muted/40 text-muted-foreground"
      )}
      role="status"
      aria-live="polite"
    >
      {active ? (
        <Loader2 className="h-4 w-4 animate-spin text-[var(--books-blue)]" />
      ) : (
        <span aria-hidden className="h-2 w-2 rounded-full bg-[var(--books-safe)]" />
      )}
      <span>
        {active ? "Processing AI tie-breaks…" : "AI tie-breaks complete"}
      </span>
      <span className="ml-auto flex gap-3 font-tabular text-xs">
        <span>pending {pending}</span>
        <span>processed {processed}</span>
        {failed > 0 && <span className="text-destructive">failed {failed}</span>}
      </span>
    </div>
  )
}