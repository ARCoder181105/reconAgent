// Thin typed wrapper over the ReconAgent FastAPI backend.
// No logic lives here — components stay presentational (documented in It9).

export interface Report {
  total_settlements: number
  total_bank_lines: number
  matched_settlements: number
  auto_matched: number
  review_queue: number
  unmatched_settlements: number
  bank_lines_matched: number
  bank_line_exceptions: number
  match_rate: number
  review_rate: number
  exception_rate: number
  verified_count: number
  verified_rate: number
  by_stage: Record<string, number>
  by_stage_auto: Record<string, number>
  by_stage_review: Record<string, number>
  by_reason: Record<string, number>
  cash: {
    rupees_auto: number
    rupees_review: number
    rupees_exceptions: number
    rupees_verified: number
  }
}

export interface Settlement {
  settlement_id: string
  utr?: string | null
  settlement_date?: string | null
  no_of_transactions?: number | null
  gross_amount?: number | null
  fees?: number | null
  tax_gst?: number | null
  refunds_deducted?: number | null
  adjustments?: number | null
  net_amount?: number | null
  status?: string | null
  bank_account_last4?: string | null
}

export interface BankStatement {
  line_id: string
  txn_date?: string | null
  value_date?: string | null
  description?: string | null
  ref_no?: string | null
  debit?: number | null
  credit?: number | null
  balance?: number | null
  bank_name?: string | null
}

export interface Match {
  match_id: number
  settlement_id: string
  line_id: string
  stage: string
  confidence: number
  resolved_at: string
}

export interface Candidate {
  settlement_id: string
  line_id?: string | null
  score?: number | null
  stage?: string | null
  net_amount?: number | null
  settlement_date?: string | null
}

export interface ExceptionRecord {
  exception_id: number
  settlement_id?: string | null
  line_id?: string | null
  reason_code: string
  confidence?: number | null
  candidates_json?: string | null
  status: string
  created_at: string
}

export interface ExceptionEvent {
  event_id: number
  exception_id: number
  event_type: string
  maker_id?: string | null
  checker_id?: string | null
  resolution_data?: string | null
  reason_text?: string | null
  timestamp: string
}

export interface TiebreaksStatus {
  pending: number
  processed: number
  failed: number
}

/** Shape returned directly by POST /run-reconciliation (omits the live
 * verified/split fields that only GET /report resolves from matches). */
export interface RunReport {
  total_settlements: number
  total_bank_lines: number
  matched_settlements: number
  auto_matched: number
  review_queue: number
  unmatched_settlements: number
  bank_lines_matched: number
  bank_line_exceptions: number
  match_rate: number
  review_rate: number
  exception_rate: number
  by_stage: Record<string, number>
  by_reason: Record<string, number>
}

const BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000/api"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(`Request failed (${res.status}): ${detail}`)
  }
  return (await res.json()) as T
}

export const api = {
  report: () => request<Report>("/report"),
  matches: (stage?: string, minConf?: number) => {
    const params = new URLSearchParams()
    if (stage) params.set("stage", stage)
    if (minConf != null) params.set("min_conf", String(minConf))
    const qs = params.toString()
    return request<Match[]>(`/matches${qs ? `?${qs}` : ""}`)
  },
  exceptions: (status?: string, reason?: string) => {
    const params = new URLSearchParams()
    if (status) params.set("status", status)
    if (reason) params.set("reason", reason)
    const qs = params.toString()
    return request<ExceptionRecord[]>(`/exceptions${qs ? `?${qs}` : ""}`)
  },
  pendingApproval: () => request<ExceptionRecord[]>("/exceptions/pending-approval"),
  exceptionEvents: (id: number) => request<ExceptionEvent[]>(`/exceptions/${id}/events`),
  resolve: (id: number, body: { maker_id: string; action: "confirm" | "reject" | "override"; resolution_data?: Record<string, unknown> }) =>
    request<ExceptionRecord>(`/exceptions/${id}/resolve`, { method: "POST", body: JSON.stringify(body) }),
  approve: (id: number, body: { checker_id: string; decision: boolean; reason_text?: string }) =>
    request<ExceptionRecord>(`/exceptions/${id}/approve`, { method: "POST", body: JSON.stringify(body) }),
  settlements: (limit = 100, offset = 0) =>
    request<Settlement[]>(`/settlements?limit=${limit}&offset=${offset}`),
  bankStatement: (limit = 100, offset = 0) =>
    request<BankStatement[]>(`/bank-statement?limit=${limit}&offset=${offset}`),
  generateData: (seed?: number) => {
    const qs = seed != null ? `?seed=${seed}` : ""
    return request<{ seed: number; settlements: number; bank_lines: number }>(`/generate-data${qs}`, {
      method: "POST",
    })
  },
  runReconciliation: (seed?: number) => {
    const qs = seed != null ? `?seed=${seed}` : ""
    return request<{ report: RunReport }>(`/run-reconciliation${qs}`, {
      method: "POST",
    })
  },
  aiTiebreaks: () => request<TiebreaksStatus>("/ai-tiebreaks"),
}

/** Parse the JSON-encoded candidates string stored on an exception row. */
export function parseCandidates(exception: ExceptionRecord): Candidate[] {
  if (!exception.candidates_json) return []
  try {
    const parsed = JSON.parse(exception.candidates_json)
    return Array.isArray(parsed) ? (parsed as Candidate[]) : []
  } catch {
    return []
  }
}