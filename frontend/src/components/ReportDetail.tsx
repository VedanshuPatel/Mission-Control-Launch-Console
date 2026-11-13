import { useEffect, useEffectEvent, useState } from 'react'
import { getReport } from '../api'
import type { Report } from '../types'
import { ApprovalPanel } from './ApprovalPanel'
import { Banners } from './Banners'
import { TraceList } from './TraceList'
import { VerdictBadge } from './VerdictBadge'

type Props = {
  reportId: string
  onUpdated: (report: Report) => void
}

function isProcessing(status: string): boolean {
  return status === 'received' || status === 'processing'
}

function briefByCountdown(report: Report): string {
  if (!report.brief_by_at) {
    return report.brief_by_minutes != null ? `${report.brief_by_minutes} minutes` : '—'
  }
  const target = new Date(report.brief_by_at).getTime()
  const ms = target - Date.now()
  if (ms <= 0) return 'due now'
  const mins = Math.ceil(ms / 60_000)
  return `${mins} min remaining (by ${new Date(report.brief_by_at).toLocaleString()})`
}

export function ReportDetail({ reportId, onUpdated }: Props) {
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Keep parent sync out of effect deps so polling stays on a 2s cadence.
  const notifyUpdated = useEffectEvent((next: Report) => {
    onUpdated(next)
  })

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setInterval> | null = null

    async function load() {
      try {
        const next = await getReport(reportId)
        if (cancelled) return null
        setReport(next)
        notifyUpdated(next)
        setError(null)
        if (isProcessing(next.status)) {
          if (timer == null) {
            timer = setInterval(() => {
              void load()
            }, 2000)
          }
        } else if (timer != null) {
          clearInterval(timer)
          timer = null
        }
        return next
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load report')
        }
        return null
      }
    }

    void load()
    return () => {
      cancelled = true
      if (timer != null) clearInterval(timer)
    }
  }, [reportId])

  if (error) {
    return <p className="field-error" role="alert">{error}</p>
  }
  if (!report) {
    return <p className="muted">Loading report…</p>
  }

  return (
    <section className="report-detail">
      <header className="detail-header">
        <h2>Report detail</h2>
        <VerdictBadge verdict={report.verdict} />
        <span className="detail-status">{report.status}</span>
      </header>

      <Banners report={report} />

      <dl className="detail-meta">
        <div>
          <dt>Subsystem</dt>
          <dd>{report.subsystem ?? '—'}</dd>
        </div>
        <div>
          <dt>Severity</dt>
          <dd>{report.effective_severity ?? report.model_severity ?? '—'}</dd>
        </div>
        <div>
          <dt>Brief-by</dt>
          <dd>{briefByCountdown(report)}</dd>
        </div>
        <div>
          <dt>Total cost</dt>
          <dd data-testid="report-cost">${report.cost_usd}</dd>
        </div>
      </dl>

      {report.violations && report.violations.length > 0 ? (
        <div className="violations">
          <h3>Violations</h3>
          <ul>
            {report.violations.map((v) => (
              <li key={v.reading}>
                {v.reading}
                {v.message ? `: ${v.message}` : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {report.briefing ? (
        <div className="briefing-block">
          <h3>Briefing</h3>
          <pre className="briefing-text">{report.briefing.text}</pre>
          <p className="muted">
            Review rounds: {report.briefing.rounds_used}
            {report.briefing.review_passed ? '' : ' · reviewer not satisfied'}
          </p>
        </div>
      ) : null}

      <ApprovalPanel report={report} onApproved={onUpdated} />
      <TraceList steps={report.trace_steps} />
    </section>
  )
}
