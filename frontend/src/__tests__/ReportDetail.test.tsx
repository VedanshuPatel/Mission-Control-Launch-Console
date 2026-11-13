import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportDetail } from '../components/ReportDetail'
import { makeReport } from './fixtures'

const getReport = vi.fn()

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    getReport: (...args: unknown[]) => getReport(...args),
  }
})

describe('ReportDetail', () => {
  beforeEach(() => {
    getReport.mockReset()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows verdict badge, violations, subsystem, severity, brief-by, briefing, rounds, and API cost', async () => {
    getReport.mockResolvedValue(
      makeReport({
        verdict: 'no_go',
        subsystem: 'propulsion',
        effective_severity: 'high',
        brief_by_at: '2099-01-01T12:05:00Z',
        cost_usd: '0.000456',
        violations: [{ reading: 'wind_knots', message: 'above limit' }],
        briefing: {
          text: 'VERDICT: NO-GO\n\nWind out of limits.',
          rounds_used: 2,
          review_passed: true,
          last_feedback: '',
          status: 'pending',
          approved_by: null,
          approved_at: null,
        },
      }),
    )

    render(<ReportDetail reportId="r1" onUpdated={() => {}} />)

    expect(await screen.findByText('NO-GO')).toBeInTheDocument()
    expect(screen.getByText(/propulsion/i)).toBeInTheDocument()
    expect(screen.getByText(/high/i)).toBeInTheDocument()
    expect(screen.getByText(/wind_knots/i)).toBeInTheDocument()
    expect(screen.getByText(/VERDICT: NO-GO/)).toBeInTheDocument()
    expect(screen.getByText(/Review rounds: 2/i)).toBeInTheDocument()
    expect(screen.getByTestId('report-cost')).toHaveTextContent('$0.000456')
    expect(screen.getByText(/min remaining/i)).toBeInTheDocument()
  })

  it('polls every 2s while processing', async () => {
    getReport
      .mockResolvedValueOnce(makeReport({ status: 'processing', briefing: null, trace_steps: [] }))
      .mockResolvedValueOnce(makeReport({ status: 'processing', briefing: null, trace_steps: [] }))
      .mockResolvedValue(makeReport({ status: 'awaiting_approval' }))

    render(<ReportDetail reportId="r1" onUpdated={() => {}} />)

    await waitFor(() => expect(getReport).toHaveBeenCalledTimes(1))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    await waitFor(() => expect(getReport).toHaveBeenCalledTimes(2))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    await waitFor(() => expect(getReport).toHaveBeenCalledTimes(3))
  })
})
