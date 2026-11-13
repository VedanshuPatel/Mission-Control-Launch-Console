import { FormEvent, useState } from 'react'
import { ApiError, approveBriefing } from '../api'
import type { Report } from '../types'

type Props = {
  report: Report
  onApproved: (report: Report) => void
}

export function ApprovalPanel({ report, onApproved }: Props) {
  const [name, setName] = useState('')
  const [ack, setAck] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (report.status === 'approved' || report.briefing?.status === 'approved') {
    return null
  }
  if (report.status !== 'awaiting_approval' || !report.briefing) {
    return null
  }

  const needsAck = report.needs_human_review
  const canSubmit = name.trim().length > 0 && (!needsAck || ack)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      const updated = await approveBriefing(report.id, {
        approver_name: name.trim(),
        acknowledge_flags: ack,
      })
      onApproved(updated)
    } catch (err) {
      if (err instanceof ApiError && err.errors.length) {
        setError(err.errors.map((e) => e.message).join('; '))
      } else {
        setError(err instanceof Error ? err.message : 'Approval failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="approval-panel" onSubmit={onSubmit}>
      <h3>Flight Director approval</h3>
      <label>
        Approver name
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoComplete="name"
        />
      </label>
      {needsAck ? (
        <label className="ack-row">
          <input
            type="checkbox"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          I acknowledge the review flags on this report
        </label>
      ) : null}
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" disabled={!canSubmit || submitting}>
        Approve
      </button>
    </form>
  )
}
