import type { Report, TraceStep } from '../types'

export function makeStep(overrides: Partial<TraceStep> & Pick<TraceStep, 'seq' | 'name' | 'kind'>): TraceStep {
  return {
    model: overrides.kind === 'model' ? 'fake-model' : null,
    input_tokens: overrides.kind === 'model' ? 12 : 0,
    output_tokens: overrides.kind === 'model' ? 4 : 0,
    cost_usd: overrides.kind === 'model' ? '0.000010' : '0.000000',
    started_at: '2026-01-01T00:00:00Z',
    ended_at: '2026-01-01T00:00:01Z',
    status: 'ok',
    summary: overrides.name,
    detail: null,
    ...overrides,
  }
}

export const TEN_STEPS: TraceStep[] = [
  makeStep({ seq: 1, name: 'classify', kind: 'model', input_tokens: 10, output_tokens: 5, cost_usd: '0.000001' }),
  makeStep({ seq: 2, name: 'limits', kind: 'code' }),
  makeStep({ seq: 3, name: 'brief_time', kind: 'code' }),
  makeStep({ seq: 4, name: 'check_injection', kind: 'model', input_tokens: 8, output_tokens: 3, cost_usd: '0.000002' }),
  makeStep({
    seq: 5,
    name: 'check_missing_details',
    kind: 'model',
    input_tokens: 9,
    output_tokens: 2,
    cost_usd: '0.000003',
  }),
  makeStep({ seq: 6, name: 'check_tone', kind: 'model', input_tokens: 7, output_tokens: 1, cost_usd: '0.000004' }),
  makeStep({ seq: 7, name: 'draft_1', kind: 'model', input_tokens: 20, output_tokens: 15, cost_usd: '0.000005' }),
  makeStep({ seq: 8, name: 'review_1', kind: 'model', input_tokens: 18, output_tokens: 6, cost_usd: '0.000006' }),
  makeStep({ seq: 9, name: 'draft_2', kind: 'model', input_tokens: 22, output_tokens: 14, cost_usd: '0.000007' }),
  makeStep({ seq: 10, name: 'human_approval', kind: 'human' }),
]

export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    created_at: '2026-01-01T12:00:00Z',
    engineer_name: 'Ada',
    station: 'PROP',
    wind_knots: 10,
    temp_c: 20,
    fuel_pct: 99,
    note: 'Valve PV-7 chattered.',
    status: 'awaiting_approval',
    error: null,
    subsystem: 'propulsion',
    model_severity: 'medium',
    effective_severity: 'medium',
    classification_fallback: false,
    verdict: 'go',
    violations: [],
    brief_by_minutes: 15,
    brief_by_at: '2026-01-01T12:15:00Z',
    flags: null,
    needs_human_review: false,
    review_reasons: null,
    total_input_tokens: 100,
    total_output_tokens: 40,
    cost_usd: '0.000123',
    briefing: {
      text: 'VERDICT: GO\n\nAll clear.\n\nRecommended action: Continue.',
      rounds_used: 1,
      review_passed: true,
      last_feedback: '',
      status: 'pending',
      approved_by: null,
      approved_at: null,
    },
    trace_steps: TEN_STEPS.slice(0, 8),
    ...overrides,
  }
}
