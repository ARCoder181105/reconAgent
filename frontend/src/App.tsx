import { AppShell, type View } from "@/components/layout/AppShell"
import { Dashboard } from "@/components/Dashboard"
import { Inspection } from "@/pages/Inspection"
import { ExceptionQueue } from "@/pages/ExceptionQueue"
import { AuditTrail } from "@/pages/AuditTrail"
import { Toaster } from "sonner"

function renderView(view: View) {
  switch (view) {
    case "summary":
      return <Dashboard />
    case "inspection":
      return <Inspection />
    case "exceptions":
      return <ExceptionQueue />
    case "audit":
      return <AuditTrail />
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