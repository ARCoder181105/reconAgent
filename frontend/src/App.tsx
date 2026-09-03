import { AppShell, type View } from "@/components/layout/AppShell"
import { Dashboard } from "@/components/Dashboard"
import { Inspection } from "@/pages/Inspection"
import { Toaster } from "sonner"

function Placeholder({ view }: { view: string }) {
  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Coming next</p>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
          {view}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          This view ships in Iteration 10 — the exception queue, Maker-Checker approval, and audit trail.
        </p>
      </header>
    </div>
  )
}

function renderView(view: View) {
  switch (view) {
    case "summary":
      return <Dashboard />
    case "inspection":
      return <Inspection />
    case "exceptions":
      return <Placeholder view="Exception queue" />
    case "audit":
      return <Placeholder view="Audit trail" />
  }
}

export default function App() {
  return (
    <>
      <AppShell>{renderView}</AppShell>
      <Toaster position="top-right" richColors />
    </>
  )
}