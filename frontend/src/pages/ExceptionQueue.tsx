import { useState } from "react"
import { CheckSquare, ClipboardCheck, PlayCircle, Undo2 } from "lucide-react"
import { toast } from "sonner"
import {
  parseCandidates,
  type ExceptionRecord,
} from "@/api/client"
import { useExceptions, type MakerAction } from "@/hooks/useExceptions"
import { useLiveSync } from "@/hooks/useLiveSync"
import { cn } from "@/lib/utils"
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
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  reasonLabel,
  reasonTone,
  tierLabel,
  CandidatesList,
} from "@/components/exceptions"

type Tab = "maker" | "checker"

const CONFIRM_TEXT: Record<MakerAction, string> = {
  confirm: "Confirm this settlement is correct.",
  reject: "Reject this pairing — it does not belong together.",
  override: "Force-assign a different resolution.",
}

export function ExceptionQueue() {
  const { open, pending, loading, error, resolve, approve, resolveMany, busyIds, reload } = useExceptions()
  useLiveSync(reload)
  const [tab, setTab] = useState<Tab>("maker")
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const toggle = (id: number) =>
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const clearSelection = () => setSelected(new Set())

  const onBulk = async (action: MakerAction) => {
    if (selected.size === 0) return
    const ok = await resolveMany([...selected], "maker", action)
    if (ok) {
      toast.success(`Proposed ${action} for ${selected.size} exception${selected.size > 1 ? "s" : ""}`)
      clearSelection()
    } else {
      toast.error("Bulk resolve failed — check the backend is running")
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Maker · Checker
        </p>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
          Exception queue
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          The engine flags anything it cannot auto-close with a reason code and ranked candidates.
          A Maker proposes a resolution; a Checker signs it off — only then are the books closed and
          the verified rate moves.
        </p>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        <TabButton active={tab === "maker"} onClick={() => setTab("maker")}>
          Open queue · Maker
        </TabButton>
        <TabButton active={tab === "checker"} onClick={() => setTab("checker")}>
          Pending approval · Checker
          {pending.length > 0 && (
            <span className="ml-1 rounded-full bg-[var(--books-blue)] px-1.5 py-0.5 text-[10px] font-semibold text-white">
              {pending.length}
            </span>
          )}
        </TabButton>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-2 rounded-lg border bg-card p-4 shadow-sm">
          <Skeleton className="h-8" />
          <Skeleton className="h-24" />
        </div>
      ) : tab === "maker" ? (
        <MakerTable
          rows={open}
          selected={selected}
          toggle={toggle}
          clearSelection={clearSelection}
          busyIds={busyIds}
          onResolve={resolve}
          onBulk={onBulk}
          onResolved={(id) => {
            toast.success(`Proposed resolution for #${id} — awaiting the checker`)
          }}
        />
      ) : (
        <CheckerTable rows={pending} busyIds={busyIds} onApprove={approve} />
      )}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
        active
          ? "border-foreground text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground cursor-pointer"
      )}
    >
      {children}
    </button>
  )
}

function MakerTable({
  rows,
  selected,
  toggle,
  clearSelection,
  busyIds,
  onResolve,
  onBulk,
  onResolved,
}: {
  rows: ExceptionRecord[]
  selected: Set<number>
  toggle: (id: number) => void
  clearSelection: () => void
  busyIds: Set<number>
  onResolve: ReturnType<typeof useExceptions>["resolve"]
  onBulk: (action: MakerAction) => void
  onResolved: (id: number) => void
}) {
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.exception_id))

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      {/* Bulk bar */}
      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b bg-accent/30 px-4 py-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          {(["confirm", "reject", "override"] as MakerAction[]).map((a) => (
            <Button key={a} size="sm" onClick={() => onBulk(a)}>
              {a === "confirm" && <CheckSquare className="h-4 w-4" />}
              {a === "reject" && <Undo2 className="h-4 w-4" />}
              {a === "override" && <PlayCircle className="h-4 w-4" />}
              Apply {a}
            </Button>
          ))}
          <Button variant="ghost" size="sm" className="ml-auto" onClick={clearSelection}>
            Clear
          </Button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">
              <Checkbox
                checked={allSelected}
                onCheckedChange={(checked) => {
                  rows.forEach((r) => {
                    if (checked && !selected.has(r.exception_id)) toggle(r.exception_id)
                    if (!checked && selected.has(r.exception_id)) toggle(r.exception_id)
                  })
                }}
                aria-label="Select all"
              />
            </TableHead>
            <TableHead>Reason</TableHead>
            <TableHead>Settlement</TableHead>
            <TableHead className="text-right">Confidence</TableHead>
            <TableHead>Candidates</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                Queue is clear — every exception has a proposal. Check the Pending Approval tab.
              </TableCell>
            </TableRow>
          )}
          {rows.map((r) => (
            <MakerRow key={r.exception_id} exc={r} selected={selected.has(r.exception_id)} toggle={toggle} busy={busyIds.has(r.exception_id)} onResolve={onResolve} onResolved={onResolved} />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function MakerRow({
  exc,
  selected,
  toggle,
  busy,
  onResolve,
  onResolved,
}: {
  exc: ExceptionRecord
  selected: boolean
  toggle: (id: number) => void
  busy: boolean
  onResolve: ReturnType<typeof useExceptions>["resolve"]
  onResolved: (id: number) => void
}) {
  const [action, setAction] = useState<MakerAction | null>(null)
  return (
    <TableRow>
      <TableCell>
        <Checkbox checked={selected} onCheckedChange={() => toggle(exc.exception_id)} aria-label={`Select ${exc.exception_id}`} />
      </TableCell>
      <TableCell>
        <Badge variant={reasonTone(exc.reason_code)} className="font-mono">
          {reasonLabel(exc.reason_code)}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs">{exc.settlement_id ?? exc.line_id ?? "—"}</TableCell>
      <TableCell className="text-right">
        <span className="font-tabular">{exc.confidence ?? "—"}</span>
        <span className="ml-1 text-xs text-muted-foreground">{tierLabel(exc.confidence)}</span>
      </TableCell>
      <TableCell className="max-w-[18rem]">
        <CandidatesList candidates={parseCandidates(exc)} compact />
      </TableCell>
      <TableCell className="text-right">
        <Button size="sm" variant="outline" disabled={busy} onClick={() => setAction("confirm")}>
          Review
        </Button>
        {action && (
          <ResolveDialog
            exc={exc}
            defaults={{ action }}
            onResolve={onResolve}
            open
            onOpenChange={(o) => {
              if (!o) setAction(null)
            }}
            onResolved={() => onResolved(exc.exception_id)}
          />
        )}
      </TableCell>
    </TableRow>
  )
}

function ResolveDialog({
  exc,
  defaults,
  onResolve,
  open,
  onOpenChange,
  onResolved,
}: {
  exc: ExceptionRecord
  defaults: { action: MakerAction }
  onResolve: ReturnType<typeof useExceptions>["resolve"]
  open: boolean
  onOpenChange: (open: boolean) => void
  onResolved: () => void
}) {
  const [action, setAction] = useState<MakerAction>(defaults.action)
  const [makerId, setMakerId] = useState("maker")
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    setSubmitting(true)
    const ok = await onResolve(exc.exception_id, makerId.trim() || "maker", action)
    setSubmitting(false)
    if (ok) {
      toast.success(`Proposed ${action} for #${exc.exception_id}`)
      onResolved()
      onOpenChange(false)
    } else {
      toast.error("Resolve failed")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Maker proposal · #{exc.exception_id}</DialogTitle>
          <DialogDescription>
            <ReasonTag exc={exc} />
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 space-y-2 overflow-y-auto text-sm">
          <p className="text-muted-foreground">Proposed decision</p>
          <div className="flex gap-2">
            {(["confirm", "reject", "override"] as MakerAction[]).map((a) => (
              <Button key={a} size="sm" variant={action === a ? "default" : "outline"} onClick={() => setAction(a)}>
                {a}
              </Button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{CONFIRM_TEXT[action]}</p>

          <div className="pt-1">
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Maker id
            </label>
            <Input value={makerId} onChange={(e) => setMakerId(e.target.value)} placeholder="maker" />
          </div>

          <div className="pt-2">
            <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">Candidates</p>
            <div className="rounded-md border bg-muted/40 p-2">
              <CandidatesList candidates={parseCandidates(exc)} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? "Submitting…" : "Propose"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CheckerTable({ rows, busyIds, onApprove }: { rows: ExceptionRecord[]; busyIds: Set<number>; onApprove: ReturnType<typeof useExceptions>["approve"] }) {
  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Reason</TableHead>
            <TableHead>Settlement</TableHead>
            <TableHead className="text-right">Confidence</TableHead>
            <TableHead>Proposed</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                Nothing pending approval. A Maker still needs to propose a resolution.
              </TableCell>
            </TableRow>
          )}
          {rows.map((r) => (
            <CheckerRow key={r.exception_id} exc={r} busy={busyIds.has(r.exception_id)} onApprove={onApprove} />
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function CheckerRow({ exc, busy, onApprove }: { exc: ExceptionRecord; busy: boolean; onApprove: ReturnType<typeof useExceptions>["approve"] }) {
  const [open, setOpen] = useState(false)
  return (
    <TableRow>
      <TableCell>
        <Badge variant={reasonTone(exc.reason_code)} className="font-mono">
          {reasonLabel(exc.reason_code)}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs">{exc.settlement_id ?? exc.line_id ?? "—"}</TableCell>
      <TableCell className="text-right font-tabular">{exc.confidence ?? "—"}</TableCell>
      <TableCell className="max-w-[16rem]">
        <CandidatesList candidates={parseCandidates(exc)} compact />
      </TableCell>
      <TableCell className="text-right">
        <Button size="sm" variant="outline" disabled={busy} onClick={() => setOpen(true)}>
          <ClipboardCheck className="h-4 w-4" /> Sign
        </Button>
        {open && <ApproveDialog exc={exc} onApprove={onApprove} open onOpenChange={setOpen} />}
      </TableCell>
    </TableRow>
  )
}

function ApproveDialog({
  exc,
  onApprove,
  open,
  onOpenChange,
}: {
  exc: ExceptionRecord
  onApprove: ReturnType<typeof useExceptions>["approve"]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [checkerId, setCheckerId] = useState("checker")
  const [decision, setDecision] = useState<boolean | null>(null)
  const [reason, setReason] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    if (decision == null) return
    setSubmitting(true)
    const ok = await onApprove(exc.exception_id, checkerId.trim() || "checker", decision, reason || undefined)
    setSubmitting(false)
    if (ok) {
      toast.success(decision ? `Closed #${exc.exception_id} — books updated` : `Rejected proposal for #${exc.exception_id}`)
      onOpenChange(false)
    } else {
      toast.error("Approval failed")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Checker sign-off · #{exc.exception_id}</DialogTitle>
          <DialogDescription>
            <ReasonTag exc={exc} />
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 space-y-2 overflow-y-auto text-sm">
          <p className="text-muted-foreground">Decision</p>
          <div className="flex gap-2">
            <Button size="sm" variant={decision === true ? "default" : "outline"} onClick={() => setDecision(true)}>
              Approve & close
            </Button>
            <Button size="sm" variant={decision === false ? "destructive" : "outline"} onClick={() => setDecision(false)}>
              Reject & reopen
            </Button>
          </div>

          <div className="pt-1">
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Checker id
            </label>
            <Input value={checkerId} onChange={(e) => setCheckerId(e.target.value)} placeholder="checker" />
          </div>

          <div className="pt-1">
            <label className="mb-1 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Note {decision === false && <span className="text-destructive">(required if rejecting)</span>}
            </label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="optional note" />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={submitting || decision == null || (decision === false && !reason.trim())}>
            {submitting ? "Submitting…" : decision === false ? "Reject" : "Approve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ReasonTag({ exc }: { exc: ExceptionRecord }) {
  return (
    <span className="flex items-center gap-2">
      <Badge variant={reasonTone(exc.reason_code)} className="font-mono">
        {reasonLabel(exc.reason_code)}
      </Badge>
      <span className="text-xs text-muted-foreground">
        confidence <span className="font-tabular">{exc.confidence ?? "—"}</span> ·{" "}
        {tierLabel(exc.confidence)}
      </span>
    </span>
  )
}