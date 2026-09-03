import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"

interface MetricCardProps {
  label: string
  value: string
  sub?: string
  accent?: "safe" | "amber" | "review" | "neutral"
  hint?: ReactNode
}

export function MetricCard({ label, value, sub, accent = "neutral", hint }: MetricCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div
          aria-hidden
          className={cn("h-1 w-full", {
            "bg-[var(--books-safe)]": accent === "safe",
            "bg-[var(--books-amber)]": accent === "amber",
            "bg-[var(--books-blue)]": accent === "review",
            "bg-primary": accent === "neutral",
          })}
        />
        <div className="px-5 py-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className={cn("font-display text-3xl font-semibold tracking-tight text-foreground font-tabular", "mt-1")}>
            {value}
          </p>
          {sub ? <p className="mt-1 text-xs text-muted-foreground">{sub}</p> : null}
          {hint ? <div className="mt-2">{hint}</div> : null}
        </div>
      </CardContent>
    </Card>
  )
}