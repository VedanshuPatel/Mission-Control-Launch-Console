import type { Report } from '../types'

type Props = {
  report?: Report | null
  provider?: string | null
}

export function Banners({ report, provider }: Props) {
  const showDemo = provider === 'fake'
  const showFlags = Boolean(report?.needs_human_review)
  const showReviewer =
    report?.briefing != null && report.briefing.review_passed === false

  if (!showDemo && !showFlags && !showReviewer) {
    return null
  }

  return (
    <div className="banners">
      {showDemo ? (
        <p className="banner demo" role="status">
          DEMO MODE — using the fake model; no live Gemini calls.
        </p>
      ) : null}
      {showFlags ? (
        <p className="banner flags" role="status">
          Flags require human review
          {report?.review_reasons?.length
            ? `: ${report.review_reasons.join(', ')}`
            : '.'}
        </p>
      ) : null}
      {showReviewer ? (
        <p className="banner reviewer" role="status">
          Reviewer not satisfied after 3 rounds
        </p>
      ) : null}
    </div>
  )
}
