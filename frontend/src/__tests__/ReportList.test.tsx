import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ReportList } from '../components/ReportList'
import { makeReport } from './fixtures'

describe('ReportList', () => {
  it('renders reports newest first with status, verdict, severity, brief-by, cost, and NEEDS REVIEW', () => {
    const reports = [
      makeReport({
        id: 'newer',
        created_at: '2026-01-02T00:00:00Z',
        status: 'awaiting_approval',
        verdict: 'no_go',
        effective_severity: 'high',
        brief_by_at: '2026-01-02T00:05:00Z',
        cost_usd: '0.000200',
        needs_human_review: true,
      }),
      makeReport({
        id: 'older',
        created_at: '2026-01-01T00:00:00Z',
        status: 'approved',
        verdict: 'go',
        effective_severity: 'low',
        brief_by_at: '2026-01-01T00:30:00Z',
        cost_usd: '0.000100',
        needs_human_review: false,
      }),
    ]

    render(<ReportList reports={reports} selectedId={null} onSelect={() => {}} />)

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent(/newer|awaiting_approval|NO-GO|high/i)
    expect(items[0]).toHaveTextContent(/0\.000200/)
    expect(items[0]).toHaveTextContent(/NEEDS REVIEW/i)
    expect(items[0]).toHaveTextContent(/brief/i)
    expect(items[1]).toHaveTextContent(/older|approved|GO|low/i)
    expect(items[1]).not.toHaveTextContent(/NEEDS REVIEW/i)
  })
})
