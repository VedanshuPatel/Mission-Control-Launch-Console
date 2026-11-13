import type { Report } from '../types'

type Props = {
  reports: Report[]
  selectedId: string | null
  onSelect: (id: string) => void
}

function verdictLabel(verdict: string | null): string {
  if (verdict === 'no_go') return 'NO-GO'
  if (verdict === 'go') return 'GO'
  return '—'
}

function formatBriefBy(report: Report): string {
  if (report.brief_by_at) {
    return `Brief by ${new Date(report.brief_by_at).toLocaleString()}`
  }
  if (report.brief_by_minutes != null) {
    return `Brief in ${report.brief_by_minutes}m`
  }
  return 'Brief by —'
}

export function ReportList({ reports, selectedId, onSelect }: Props) {
  const ordered = [...reports].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )

  return (
    <section className="report-list">
      <h2>Reports</h2>
      {ordered.length === 0 ? <p className="muted">No reports yet.</p> : null}
      <ul>
        {ordered.map((report) => (
          <li key={report.id}>
            <button
              type="button"
              className={selectedId === report.id ? 'report-row selected' : 'report-row'}
              onClick={() => onSelect(report.id)}
            >
              <span className="row-status">{report.status}</span>
              <span className="row-verdict">{verdictLabel(report.verdict)}</span>
              <span className="row-severity">{report.effective_severity ?? '—'}</span>
              <span className="row-brief">{formatBriefBy(report)}</span>
              <span className="row-cost">${report.cost_usd}</span>
              {report.needs_human_review ? (
                <span className="needs-review">NEEDS REVIEW</span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
