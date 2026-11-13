/** API shapes from the backend ReportOut / TraceStepOut / BriefingOut contracts. */

export type ReportStatus =
  | 'received'
  | 'processing'
  | 'awaiting_approval'
  | 'approved'
  | 'failed'

export interface TraceStep {
  seq: number
  name: string
  kind: string
  model: string | null
  input_tokens: number
  output_tokens: number
  cost_usd: string
  started_at: string
  ended_at: string
  status: string
  summary: string
  detail: Record<string, unknown> | null
}

export interface Briefing {
  text: string
  rounds_used: number
  review_passed: boolean
  last_feedback: string
  status: string
  approved_by: string | null
  approved_at: string | null
}

export interface Violation {
  reading: string
  message?: string
  [key: string]: unknown
}

export interface Report {
  id: string
  created_at: string
  engineer_name: string
  station: string
  wind_knots: number
  temp_c: number
  fuel_pct: number
  note: string
  status: ReportStatus | string
  error: string | null
  subsystem: string | null
  model_severity: string | null
  effective_severity: string | null
  classification_fallback: boolean
  verdict: string | null
  violations: Violation[] | null
  brief_by_minutes: number | null
  brief_by_at: string | null
  flags: Record<string, unknown> | null
  needs_human_review: boolean
  review_reasons: string[] | null
  total_input_tokens: number
  total_output_tokens: number
  cost_usd: string
  briefing: Briefing | null
  trace_steps: TraceStep[]
}

export interface ReportCreate {
  engineer_name: string
  station: string
  wind_knots: number
  temp_c: number
  fuel_pct: number
  note: string
}

export interface ApprovePayload {
  approver_name: string
  acknowledge_flags: boolean
}

export interface FieldError {
  field: string
  message: string
}

export interface Health {
  status: string
  provider: string
}
