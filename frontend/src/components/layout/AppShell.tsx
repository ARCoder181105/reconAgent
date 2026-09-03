import { useState, type ReactNode } from "react"
import { LayoutDashboard, Table as TableIcon, ShieldCheck, Database } from "lucide-react"
import { cn } from "@/lib/utils"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"

export type View = "summary" | "inspection" | "exceptions" | "audit"

interface NavItem {
  key: View
  label: string
  icon: typeof LayoutDashboard
  available: boolean
}

const NAV: NavItem[] = [
  { key: "summary", label: "Summary", icon: LayoutDashboard, available: true },
  { key: "inspection", label: "Data inspection", icon: Database, available: true },
  { key: "exceptions", label: "Exceptions", icon: ShieldCheck, available: false },
  { key: "audit", label: "Audit trail", icon: TableIcon, available: false },
]

export function AppShell({ children }: { children: (view: View) => ReactNode }) {
  const [view, setView] = useState<View>("summary")

  return (
    <div className="flex min-h-dvh">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-background md:flex">
        <div className="px-5 py-5">
          <p className="font-display text-base font-semibold tracking-tight text-foreground">ReconAgent</p>
          <p className="text-xs text-muted-foreground">Reconciliation workbench</p>
        </div>
        <Separator />
        <nav className="flex flex-col gap-1 p-3" aria-label="Primary">
          {NAV.map((item) => {
            const Icon = item.icon
            return (
              <Button
                key={item.key}
                variant="ghost"
                className={cn("justify-start gap-2", view === item.key && "bg-accent font-medium")}
                onClick={() => item.available && setView(item.key)}
                disabled={!item.available}
                aria-current={view === item.key ? "page" : undefined}
              >
                <Icon className="h-4 w-4" />
                {item.label}
                {!item.available && <span className="ml-auto text-[10px] uppercase text-muted-foreground">soon</span>}
              </Button>
            )
          })}
        </nav>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8">{children(view)}</div>
      </main>
    </div>
  )
}