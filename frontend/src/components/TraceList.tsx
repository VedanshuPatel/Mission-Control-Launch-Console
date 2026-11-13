import type { TraceStep } from '../types'
import { TraceCard } from './TraceCard'

type Props = {
  steps: TraceStep[]
}

const CHECK_NAMES = new Set(['check_injection', 'check_missing_details', 'check_tone'])

export function TraceList({ steps }: Props) {
  const ordered = [...steps].sort((a, b) => a.seq - b.seq)
  const before: TraceStep[] = []
  const checks: TraceStep[] = []
  const after: TraceStep[] = []

  for (const step of ordered) {
    if (CHECK_NAMES.has(step.name)) {
      checks.push(step)
    } else if (checks.length === 0) {
      before.push(step)
    } else {
      after.push(step)
    }
  }

  return (
    <section className="trace-list">
      <h2>Pipeline trace</h2>
      {before.map((step) => (
        <TraceCard key={step.seq} step={step} />
      ))}
      {checks.length > 0 ? (
        <div className="trace-parallel" data-testid="checks-parallel">
          <p className="parallel-label">ran in parallel</p>
          {checks.map((step) => (
            <TraceCard key={step.seq} step={step} />
          ))}
        </div>
      ) : null}
      {after.map((step) => (
        <TraceCard key={step.seq} step={step} />
      ))}
    </section>
  )
}
